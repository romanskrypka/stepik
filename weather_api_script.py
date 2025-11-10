#!/usr/bin/env python3
"""
Скрипт API для получения информации о погоде в формате JSON.
Использует LangChain и Pydantic для структурированного вывода.
"""

import os
import sys
import json
from typing import Optional
from dotenv import load_dotenv
from langchain_openai import ChatOpenAI
from langchain_core.prompts import PromptTemplate
from langchain_core.output_parsers import PydanticOutputParser
from pydantic import BaseModel, Field

# Загрузка переменных окружения
load_dotenv()

# Определение Pydantic модели для информации о погоде
class WeatherInfo(BaseModel):
    city: str = Field(..., description="Название города")
    temperature: float = Field(..., description="Температура в градусах Цельсия")
    condition: str = Field(..., description="Условия погоды (например, солнечно, дождливо, облачно)")

def get_weather_info(city: str) -> str:
    """
    Получает информацию о погоде для заданного города и возвращает её в формате JSON.
    
    Args:
        city (str): Название города
        
    Returns:
        str: JSON-строка с информацией о погоде или ошибкой
    """
    try:
        # Инициализация модели
        model = os.getenv("OPENAI_API_MODEL", "gpt-4o-mini")
        llm = ChatOpenAI(model=model, temperature=0.7)
        
        # Создание парсера Pydantic
        parser = PydanticOutputParser(pydantic_object=WeatherInfo)
        format_instructions = parser.get_format_instructions()
        
        # Создание шаблона промпта
        prompt = PromptTemplate(
            template="Получи информацию о погоде для города {city}.\n{format_instructions}",
            input_variables=["city"],
            partial_variables={"format_instructions": format_instructions}
        )
        
        # Создание цепочки
        chain = prompt | llm | parser
        
        # Вызов цепочки
        result = chain.invoke({"city": city})
        
        # Возврат результата в формате JSON
        return result.model_dump_json()
        
    except Exception as e:
        # Возврат ошибки в формате JSON
        error_response = {"error": f"Ошибка при получении информации о погоде: {str(e)}"}
        return json.dumps(error_response, ensure_ascii=False)

def main():
    """
    Основная функция скрипта.
    """
    # Проверка аргументов командной строки
    if len(sys.argv) > 1:
        city = sys.argv[1]
    else:
        # Если аргумент не передан, запрашиваем у пользователя
        city = input("Введите название города: ").strip()
    
    if not city:
        error_response = {"error": "Не указано название города"}
        print(json.dumps(error_response, ensure_ascii=False))
        return
    
    # Получение информации о погоде
    result = get_weather_info(city)
    print(result)

if __name__ == "__main__":
    main()