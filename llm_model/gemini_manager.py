from google import genai
from google.genai import types
from llm_model.model_manager import LlmModelManager
from utils import Utils

class GeminiModelManager(LlmModelManager):
    def __init__(self, api_key: str, default_model_name: str = "gemini-2.5-flash"):
        self.client = genai.Client(api_key=api_key)
        self.models = self.client.models
        self.default_model_name = default_model_name

    def get_model(self, model_name: str = None):
        return self.models.get(model=model_name or self.default_model_name)

    def generate(self, prompt: str, model_name: str = None, thinking_budget: int = 0) -> str:
        model = self.get_model(model_name)
        response = self.models.generate_content(
            model=model_name or self.default_model_name,
            contents=prompt,
            config=types.GenerateContentConfig(
            thinking_config=types.ThinkingConfig(thinking_budget=thinking_budget)  # 0 for no thinking, -1 for dynamic thinking
            )
        )
        return response.text

if __name__ == "__main__":

    # Nhập API key từ biến môi trường hoặc trực tiếp
    api_key = Utils.load_api_key_from_env("GEMINI_API_KEY")
    model_name = "gemini-2.5-flash"
    
    gemini = GeminiModelManager(api_key=api_key, default_model_name=model_name)

    while True:
        prompt = input("\n📝 Nhập prompt (hoặc 'exit' để thoát): ").strip()
        if prompt.lower() == "exit":
            print("👋 Kết thúc.")
            break

        try:
            output = gemini.generate(prompt=prompt, model_name=model_name)
            print("\n🧠 Phản hồi từ Gemini:")
            print(output)
        except Exception as e:
            print(f"❌ Lỗi: {e}")