import argparse
from transformers import AutoTokenizer, AutoModelForSeq2SeqLM
import torch

def run_inference(model_path: str, input_text: str, max_length: int = 100):
    print(f"Loading model from: {model_path}")
    tokenizer = AutoTokenizer.from_pretrained(model_path)
    model = AutoModelForSeq2SeqLM.from_pretrained(model_path)

    inputs = tokenizer(input_text, return_tensors="pt", padding=True)
    with torch.no_grad():
        outputs = model.generate(**inputs, max_length=max_length)

    result = tokenizer.decode(outputs[0], skip_special_tokens=True)
    print(f"\nInput: {input_text}")
    print(f"Output: {result}")
    return result


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--model_path", type=str, required=True)
    parser.add_argument("--input_text", type=str, required=True)
    parser.add_argument("--max_length", type=int, default=100)
    args = parser.parse_args()

    run_inference(args.model_path, args.input_text, args.max_length)