import json
import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig

def load_model(model_name, quantization):
    """Loads the specified model with optional quantization."""
    print(f"Loading model: {model_name}...")
    print(f"Quantization: {quantization}")

    bnb_config = None
    if quantization == "8bit":
        bnb_config = BitsAndBytesConfig(load_in_8bit=True)
    elif quantization == "4bit":
        bnb_config = BitsAndBytesConfig(load_in_4bit=True, bnb_4bit_compute_dtype=torch.float16)

    try:
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModelForCausalLM.from_pretrained(
            model_name,
            quantization_config=bnb_config,
            device_map="auto", # Automatically use the GPU
        )
        return tokenizer, model
    except Exception as e:
        print(f"Error loading model: {e}")
        return None, None

def main():
    """Main function to run the interactive console."""
    try:
        with open("config.json") as f:
            config = json.load(f)
    except FileNotFoundError:
        print("Error: config.json not found.")
        return

    model_name = config.get("model_name", "EleutherAI/gpt-neo-125M")
    quantization = config.get("quantization", "none")

    tokenizer, model = load_model(model_name, quantization)
    if not model or not tokenizer:
        return

    print("\nModel loaded successfully. Starting interactive console.")
    print("Type 'exit' or 'quit' to return to the main menu.")
    print("--------------------------------------------------")

    while True:
        try:
            prompt = input("You: ")
            if prompt.lower() in ["exit", "quit"]:
                break

            inputs = tokenizer(prompt, return_tensors="pt").to("cuda")
            
            # Generate response
            outputs = model.generate(
                **inputs,
                max_new_tokens=100,
                do_sample=True,
                temperature=0.7,
                top_p=0.9,
            )
            response = tokenizer.decode(outputs[0], skip_special_tokens=True)
            
            # The response often includes the prompt, so we remove it.
            response = response[len(prompt):].strip()

            print(f"LLM: {response}")

        except KeyboardInterrupt:
            break
        except Exception as e:
            print(f"An error occurred during generation: {e}")

    print("\n--------------------------------------------------")
    print("Exiting interactive console.")

if __name__ == "__main__":
    main()
