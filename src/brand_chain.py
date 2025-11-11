import os
import json
import yaml
import pathlib
from typing import List, Dict, Optional
from dotenv import load_dotenv
from pydantic import BaseModel, Field
from langchain_openai import ChatOpenAI
from langchain_core.prompts import ChatPromptTemplate

# Базовая директория проекта
BASE = pathlib.Path(__file__).parent.parent.resolve()

# Проверка существования файла .env
env_path = BASE / ".env"
if env_path.exists():
    # Загрузка переменных окружения
    load_dotenv(env_path, override=True)
    print(f"✅ Переменные окружения загружены из: {env_path}")
else:
    print(f"❌ Файл .env не найден по пути: {env_path}")
    raise FileNotFoundError(f"Файл .env не найден по пути: {env_path}")

# Загрузка стилевого гайда
def load_style_guide():
    with open(BASE / "data" / "style_guide.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

STYLE = load_style_guide()

# Модель для структурированного ответа
class BrandResponse(BaseModel):
    answer: str = Field(description="Краткий ответ")
    tone: str = Field(description="Контроль: совпадает ли тон (да/нет) + одна фраза почему")
    actions: List[str] = Field(description="Список следующих шагов для клиента (0–3 пункта)")

# Загрузка FAQ
def load_faq():
    with open(BASE / "data" / "faq.json", "r", encoding="utf-8") as f:
        return json.load(f)

FAQ_DATA = load_faq()

# Загрузка заказов
def load_orders():
    with open(BASE / "data" / "orders.json", "r", encoding="utf-8") as f:
        return json.load(f)

ORDERS_DATA = load_orders()

# Загрузка few-shot примеров
def load_few_shots():
    few_shots = []
    with open(BASE / "data" / "few_shots.jsonl", "r", encoding="utf-8") as f:
        for line in f:
            if line.strip():
                few_shots.append(json.loads(line.strip()))
    return few_shots

FEW_SHOTS = load_few_shots()

# Создание системного промпта из стилевого гайда
def create_system_prompt():
    system_prompt = f"""Вы - {STYLE['tone']['persona']} ассистент интернет-магазина {STYLE['brand']}.
    
Правила ответа:
1. Максимум {STYLE['tone']['sentences_max']} предложения в ответе
2. Используйте пункты, если это уместно: {STYLE['tone']['bullets']}
3. Избегайте: {', '.join(STYLE['tone']['avoid'])}
4. Обязательно включайте: {', '.join(STYLE['tone']['must_include'])}
5. Если нет точной информации, используйте: "{STYLE['fallback']['no_data']}"

Формат ответа:
Верните JSON объект с тремя полями:
- answer: краткий ответ (строка)
- tone: совпадает ли тон (да/нет) + краткое объяснение (строка)
- actions: список шагов (массив строк, 0-3 элемента)"""
    
    return system_prompt

# Создание шаблона промпта
def create_prompt_template():
    system_prompt = create_system_prompt()
    
    # Добавляем few-shot примеры (только первые 2 для сокращения длины)
    few_shot_text = "\n\nПримеры:\n"
    for i, shot in enumerate(FEW_SHOTS[:2]):
        few_shot_text += f"Пользователь: {shot['user']}\nАссистент: {shot['assistant']}\n\n"
    
    # Создаем шаблон
    return ChatPromptTemplate.from_messages([
        ("system", system_prompt),
        ("human", few_shot_text + "\nКонтекст FAQ:\n{faq_context}\n\nКонтекст заказов:\n{order_context}\n\nТекущий диалог:\n{history}\n\nПользователь: {input}\nАссистент:")
    ])

# Поиск ответа в FAQ
def get_faq_answer(question: str) -> Optional[str]:
    for item in FAQ_DATA:
        if item["q"].lower() in question.lower() or question.lower() in item["q"].lower():
            return item["a"]
    return None

# Получение статуса заказа
def get_order_status(order_id: str) -> Optional[str]:
    if order_id in ORDERS_DATA:
        order = ORDERS_DATA[order_id]
        if order["status"] == "in_transit":
            return f"Заказ {order_id} находится в пути. Ожидаемая доставка через {order['eta_days']} дня(ей). Перевозчик: {order['carrier']}."
        elif order["status"] == "delivered":
            return f"Заказ {order_id} был доставлен {order['delivered_at']}."
        elif order["status"] == "processing":
            return f"Заказ {order_id} находится в обработке. {order['note']}."
    return None

# Создание контекста FAQ
def create_faq_context(question: str) -> str:
    faq_answer = get_faq_answer(question)
    if faq_answer:
        return f"Ответ на похожий вопрос: {faq_answer}"
    return "Нет подходящего ответа в FAQ"

# Создание контекста заказов
def create_order_context(user_input: str) -> str:
    # Проверяем, есть ли номер заказа в запросе
    words = user_input.split()
    for word in words:
        if word.isdigit() and word in ORDERS_DATA:
            return get_order_status(word)
    
    # Если номер заказа не найден, возвращаем пустую строку
    return ""

# Инициализация модели
llm = ChatOpenAI(
    openai_api_key=os.getenv("OPENAI_API_KEY"),
    model="gpt-4o-mini",
    temperature=0.7,
    max_tokens=2000
)

# Создание цепочки
def create_chain():
    prompt = create_prompt_template()
    return prompt | llm.with_structured_output(BrandResponse)

chain = create_chain()

# Основная функция для получения ответа
def ask(user_input: str, history: str = "") -> BrandResponse:
    # Создаем контексты
    faq_context = create_faq_context(user_input)
    order_context = create_order_context(user_input)
    
    # Вызываем цепочку
    response = chain.invoke({
        "faq_context": faq_context,
        "order_context": order_context,
        "history": history,
        "input": user_input
    })
    
    return response

# Демонстрация работы
if __name__ == "__main__":
    print("Демонстрация работы брендированной цепочки:")
    print("=" * 50)
    
    # Примеры запросов
    test_queries = [
        "Как оформить возврат?",
        "Сколько идёт доставка?",
        "Где ввести промокод?",
        "Заказ 12345 — что со статусом?"
    ]
    
    for query in test_queries:
        print(f"\nВопрос: {query}")
        try:
            response = ask(query)
            print(f"Ответ: {response.answer}")
            print(f"Тон: {response.tone}")
            print(f"Действия: {response.actions}")
        except Exception as e:
            print(f"Ошибка: {e}")
        print("-" * 30)