import os
import logging
from openai import OpenAI
from tree_of_thoughts.models.abstract_language_model import AbstractLanguageModel

logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(levelname)s - %(message)s')
logger = logging.getLogger(__name__)


class OllamaLanguageModel(AbstractLanguageModel):
    """Language model using Ollama (local or remote models)"""

    def __init__(self, api_url="", model="llama2", max_tokens=1024, temperature=0.7,
                 top_p=1, strategy="cot", evaluation_strategy="value", enable_ReAct_prompting=True):
        if api_url == "" or api_url is None:
            api_url = os.environ.get("OLLAMA_API_URL", "http://localhost:11434")

        self.api_url = api_url
        self.client = OpenAI(
            api_key="ollama",  # Ollama doesn't require API key
            base_url=f"{api_url}/v1",
        )
        self.model = model
        self.max_tokens = max_tokens
        self.temperature = temperature
        self.top_p = top_p
        self.strategy = strategy
        self.evaluation_strategy = evaluation_strategy

        self.ReAct_prompt = ''
        if enable_ReAct_prompting:
            self.ReAct_prompt = "Write down your observations in format 'Observation:xxxx', then write down your thoughts in format 'Thoughts:xxxx'."

        logger.info(f"Initialized OllamaLanguageModel with model: {self.model} at {self.api_url}")

    def ollama_api_call(self, prompt, max_tokens=None, temperature=None):
        """Call Ollama API"""
        max_tokens = max_tokens or self.max_tokens
        temperature = temperature if temperature is not None else self.temperature

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "user", "content": prompt}
                ],
                max_tokens=max_tokens,
                temperature=temperature,
                top_p=self.top_p,
            )
            return response.choices[0].message.content
        except Exception as e:
            logger.error(f"Ollama API error: {e}")
            raise

    def generate_text(self, prompt, k):
        """Generate k text responses"""
        thoughts = []
        for _ in range(k):
            try:
                response = self.ollama_api_call(prompt)
                thoughts.append(response)
            except Exception as e:
                logger.error(f"Error generating text: {e}")
        return thoughts

    def generate_thoughts(self, state, k, initial_prompt, rejected_solutions=None):
        """Generate k thoughts based on current state"""
        if isinstance(state, str):
            state_text = state
        else:
            state_text = '\n'.join(state)

        logger.info(f"Generating thought for state: {state}")

        prompt = f"""You're an TreeofThoughts, an superintelligent AI model devoted to helping Humans by any means necessary. You're purpose is to generate a series of solutions to comply with the user's instructions, you must generate solutions on the basis of determining the most reliable solution in the shortest amount of time, while taking rejected solutions into account and learning from them.
        Considering the reasoning provided:\n\n
        ###'{state_text}'\n\n###
        Devise the best possible solution for the task: {initial_prompt}, Here are evaluated solutions that were rejected:
        ###{rejected_solutions}###,
        complete the {initial_prompt} without making the same mistakes you did with the evaluated rejected solutions. Be simple. Be direct. Provide intuitive solutions as soon as you think of them."""

        prompt += self.ReAct_prompt
        thoughts = self.generate_text(prompt, k)
        return thoughts

    def evaluate_states(self, states, initial_prompt):
        """Evaluate and score multiple states"""
        if not states:
            return {}

        if self.evaluation_strategy == 'value':
            state_values = {}
            for state in states:
                if isinstance(state, str):
                    state_text = state
                else:
                    state_text = '\n'.join(state)

                logger.info(f"Evaluating state: {state}")

                prompt = f"""To achieve the following goal: '{initial_prompt}', pessimistically value the context of the past solutions and more importantly the latest generated solution you had AS A FLOAT BETWEEN 0 AND 1\n
                    Past solutions:\n\n
                    {state_text}\n
                    If the solutions is not directly concretely making fast progress in achieving the goal, give it a lower score.
                    Evaluate all solutions AS A FLOAT BETWEEN 0 and 1:\n, DO NOT RETURN ANYTHING ELSE"""

                try:
                    response = self.ollama_api_call(prompt, max_tokens=10, temperature=1)
                    value = float(response.strip())
                    logger.info(f"Evaluated state value: {value}")
                except ValueError:
                    value = 0.0
                    logger.warning(f"Could not parse evaluation response as float: {response}")

                state_values[state] = value
            return state_values

        elif self.evaluation_strategy == 'vote':
            states_text = '\n'.join([' '.join(state) if isinstance(state, list) else state for state in states])

            prompt = f"""Given the following states of reasoning, vote for the best state utilizing a scalar value 1-10:\n{states_text}\n\nVote on the probability of this state of reasoning achieving {initial_prompt} and become very pessimistic. RETURN NOTHING ELSE"""

            try:
                response = self.ollama_api_call(prompt, max_tokens=50, temperature=1)
                best_state_text = response.strip()

                # Try to match best state to one of the given states
                best_state = None
                for state in states:
                    state_str = state if isinstance(state, str) else ' '.join(state)
                    if state_str in best_state_text:
                        best_state = state
                        break

                if best_state is None:
                    best_state = states[0]

                return {state: 1 if state == best_state else 0 for state in states}
            except Exception as e:
                logger.error(f"Error in vote evaluation: {e}")
                return {state: 0 for state in states}

        else:
            return {state: 0 for state in states}
