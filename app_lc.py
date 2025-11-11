#!/usr/bin/env python3
import os
import json
import argparse
from datetime import datetime
from dotenv import load_dotenv
from src.brand_chain import ask, get_order_status

# Загрузка переменных окружения
load_dotenv()

# Константы
LOGS_DIR = "logs"
os.makedirs(LOGS_DIR, exist_ok=True)

class EcomBrandBot:
    def __init__(self):
        self.brand_name = os.getenv("BRAND_NAME", "Shoply")
        self.conversation_history = []
        
        # Создание уникального лог-файла для этой сессии
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        self.log_file = f"{LOGS_DIR}/session_{timestamp}_lc.jsonl"
    
    def process_command(self, user_input):
        """Обработка специальных команд"""
        if user_input.startswith("/order "):
            order_id = user_input.split(" ")[1]
            order_status = get_order_status(order_id)
            if order_status:
                return order_status
            else:
                return f"Извините, заказ с номером {order_id} не найден. Пожалуйста, проверьте номер заказа и попробуйте снова."
        
        return None
    
    def format_history(self):
        """Форматирование истории разговора для включения в контекст"""
        if not self.conversation_history:
            return ""
        
        history_text = ""
        for i, msg in enumerate(self.conversation_history[-6:]):  # Последние 3 пары вопрос-ответ
            if msg["role"] == "user":
                history_text += f"Пользователь: {msg['content']}\n"
            else:
                history_text += f"Ассистент: {msg['content']}\n"
        
        return history_text
    
    def get_bot_response(self, user_input):
        """Получение ответа от брендированного бота"""
        # Проверка специальных команд
        command_response = self.process_command(user_input)
        if command_response:
            return command_response, None
        
        # Форматирование истории
        history = self.format_history()
        
        try:
            # Получение ответа от цепочки
            response = ask(user_input, history)
            
            # Формирование ответа в виде строки
            bot_reply = response.answer
            
            # Подготовка данных для логирования
            usage = {
                "model": "gpt-4o-mini",  # Жестко задаем модель для логов
                "structured_response": {
                    "answer": response.answer,
                    "tone": response.tone,
                    "actions": response.actions
                }
            }
            
            return bot_reply, usage
        
        except Exception as e:
            return "Извините, произошла ошибка при обработке вашего запроса. Пожалуйста, попробуйте позже.", None
    
    def log_interaction(self, user_input, bot_response, usage=None):
        """Логирование взаимодействия"""
        log_entry = {
            "timestamp": datetime.now().isoformat(),
            "user_message": user_input,
            "bot_response": bot_response,
            "usage": usage
        }
        
        with open(self.log_file, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")
    
    def run(self):
        """Запуск бота"""
        print(f"Добро пожаловать в брендированный чат-бот магазина {self.brand_name}!")
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
                bot_response, usage = self.get_bot_response(user_input)
                
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
    parser = argparse.ArgumentParser(description="E-commerce branded support chatbot with LangChain")
    parser.add_argument("--demo", action="store_true", 
                        help="Демонстрационный режим с предопределенными вопросами")
    args = parser.parse_args()
    
    try:
        bot = EcomBrandBot()
        
        if args.demo:
            # Демонстрационный режим
            print("Демонстрация работы брендированного бота:")
            print("=" * 50)
            
            demo_questions = [
                "Как оформить возврат?",
                "Сколько идёт доставка?",
                "Где ввести промокод?",
                "/order 12345"
            ]
            
            for question in demo_questions:
                print(f"\nВы: {question}")
                response, _ = bot.get_bot_response(question)
                print(f"Бот: {response}")
                
                # Добавляем в историю для контекста
                bot.conversation_history.append({"role": "user", "content": question})
                bot.conversation_history.append({"role": "assistant", "content": response})
            
            print("\n" + "=" * 50)
            print("Демонстрация завершена. Запуск интерактивного режима...")
            
        bot.run()
    except Exception as e:
        print(f"Ошибка при запуске бота: {e}")

if __name__ == "__main__":
    main()