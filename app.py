#!/usr/bin/env python3
import os
import json
import yaml
import argparse
from datetime import datetime
from dotenv import load_dotenv
from openai import OpenAI

# Загрузка переменных окружения
load_dotenv()

# Константы
FAQ_FILE = "data/faq.json"
ORDERS_FILE = "data/orders.json"
LOGS_DIR = "logs"
PROMPTS_FILE = "prompts.yaml"

class EcomBot:
    def __init__(self):
        # Инициализация OpenAI клиента
        self.client = OpenAI(api_key=os.getenv("OPENAI_API_KEY"))
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
        self.brand_name = os.getenv("BRAND_NAME", "Shoply")
        
        # Загрузка промптов из YAML
        self.prompts = self.load_prompts()
        
        # Загрузка FAQ
        with open(FAQ_FILE, "r", encoding="utf-8") as f:
            self.faq_data = json.load(f)
        
        # Загрузка заказов
        with open(ORDERS_FILE, "r", encoding="utf-8") as f:
            self.orders_data = json.load(f)
        
        # История диалога
        self.conversation_history = []
        
        # Создание уникального лог-файла для этой сессии
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"{LOGS_DIR}/session_{timestamp}.jsonl"
    
    def load_prompts(self):
        """Загрузка промптов из YAML файла с поддержкой версионирования"""
        try:
            with open(PROMPTS_FILE, "r", encoding="utf-8") as f:
                config = yaml.safe_load(f)
            
            prompts = config.get("prompts", {})
            
            # Обработка версионированных промптов
            for prompt_name, prompt_data in prompts.items():
                # Проверяем, есть ли переменная окружения для версии промпта
                env_version = os.getenv(f"PROMPT_{prompt_name.upper()}_VERSION")
                if env_version and env_version in prompt_data.get("versions", {}):
                    # Используем версию из переменной окружения
                    prompts[prompt_name]["current"] = env_version
                # Если переменная не задана, используем версию по умолчанию из YAML
            
            print(f"Загружены промпты из {PROMPTS_FILE}")
            for name, data in prompts.items():
                print(f"  - {name}: версия {data['current']}")
            
            return prompts
        except Exception as e:
            print(f"Ошибка при загрузке промптов: {e}. Используются стандартные промпты.")
            # Возвращаем базовые промпты, если не удалось загрузить из файла
            return {
                "main_agent": {
                    "current": "default",
                    "versions": {
                        "default": f"Вы - вежливый и краткий ассистент интернет-магазина {self.brand_name}. Отвечайте кратко и по делу."
                    }
                }
            }
    
    def get_prompt(self, prompt_name):
        """Получение промпта по имени и текущей версии"""
        if prompt_name in self.prompts:
            prompt_data = self.prompts[prompt_name]
            current_version = prompt_data["current"]
            return prompt_data["versions"].get(current_version, "")
        return ""
    
    def get_faq_answer(self, question):
        """Поиск ответа на вопрос в FAQ"""
        for item in self.faq_data:
            if item["q"].lower() in question.lower() or question.lower() in item["q"].lower():
                return item["a"]
        return None
    
    def get_order_status(self, order_id):
        """Получение статуса заказа по ID"""
        if order_id in self.orders_data:
            order = self.orders_data[order_id]
            if order["status"] == "in_transit":
                return f"Заказ {order_id} находится в пути. Ожидаемая доставка через {order['eta_days']} дня(ей). Перевозчик: {order['carrier']}."
            elif order["status"] == "delivered":
                return f"Заказ {order_id} был доставлен {order['delivered_at']}."
            elif order["status"] == "processing":
                return f"Заказ {order_id} находится в обработке. {order['note']}."
        return None
    
    def log_interaction(self, user_message, bot_response, usage=None):
        """Логирование взаимодействия"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_message,
            "bot_response": bot_response,
            "usage": usage
        }
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def process_command(self, user_input):
        """Обработка специальных команд"""
        if user_input.startswith("/order "):
            order_id = user_input.split(" ")[1]
            order_status = self.get_order_status(order_id)
            if order_status:
                return order_status
            else:
                return f"Извините, заказ с номером {order_id} не найден. Пожалуйста, проверьте номер заказа и попробуйте снова."
        
        return None
    
    def get_bot_response(self, user_input):
        """Получение ответа от бота"""
        # Проверка специальных команд
        command_response = self.process_command(user_input)
        if command_response:
            return command_response
        
        # Проверка FAQ
        faq_response = self.get_faq_answer(user_input)
        if faq_response:
            return faq_response
        
        # Если не найдено в FAQ, обращаемся к LLM
        # Получение системного промпта
        system_message = self.get_prompt("main_agent").format(brand_name=self.brand_name)
        if not system_message:
            system_message = f"Вы - вежливый и краткий ассистент интернет-магазина {self.brand_name}. Отвечайте кратко и по делу."
        
        # Подготовка сообщений для модели
        messages = [{"role": "system", "content": system_message}]
        
        # Добавление истории разговора (ограничиваем 3 последними репликами)
        for msg in self.conversation_history[-6:]:  # 3 пары вопрос-ответ
            messages.append(msg)
        
        # Добавление текущего вопроса
        messages.append({"role": "user", "content": user_input})
        
        try:
            # Вызов API
            response = self.client.chat.completions.create(
                model=self.model,
                messages=messages,
                temperature=0.7,
                max_tokens=300
            )
            
            # Извлечение ответа и информации об использовании токенов
            bot_reply = response.choices[0].message.content
            usage = {
                "prompt_tokens": response.usage.prompt_tokens,
                "completion_tokens": response.usage.completion_tokens,
                "total_tokens": response.usage.total_tokens
            }
            
            return bot_reply.strip(), usage
        
        except Exception as e:
            return "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.", None
    
    def run(self):
        """Запуск бота"""
        print(f"Добро пожаловать в чат-бот магазина {self.brand_name}!")
        print("Вы можете задавать вопросы о доставке, возврате, оплате и т.д.")
        print("Для проверки статуса заказа используйте команду: /order <номер_заказа>")
        print("Для выхода введите 'выход' или нажмите Ctrl+C\n")
        
        while True:
            try:
                user_input = input("Вы: ").strip()
                
                if not user_input:
                    continue
                
                if user_input.lower() in ["выход", "exit", "quit"]:
                    print("Бот: До свидания! Спасибо за обращение.")
                    break
                
                # Получение ответа от бота
                result = self.get_bot_response(user_input)
                
                if isinstance(result, tuple):
                    bot_response, usage = result
                else:
                    bot_response, usage = result, None
                
                print(f"Бот: {bot_response}\n")
                
                # Логирование взаимодействия
                self.log_interaction(user_input, bot_response, usage)
                
                # Добавление в историю разговора
                self.conversation_history.append({"role": "user", "content": user_input})
                self.conversation_history.append({"role": "assistant", "content": bot_response})
                
            except KeyboardInterrupt:
                print("\n\nБот: До свидания! Спасибо за обращение.")
                break
            except Exception as e:
                print(f"Бот: Извините, произошла непредвиденная ошибка. Попробуйте еще раз.")
                self.log_interaction(user_input, f"Ошибка: {str(e)}", None)

def main():
    parser = argparse.ArgumentParser(description="E-commerce support chatbot")
    parser.add_argument("--faq-only", action="store_true", 
                        help="Режим только с FAQ (без использования LLM)")
    args = parser.parse_args()
    
    try:
        bot = EcomBot()
        bot.run()
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    main()