#!/usr/bin/env python3
"""
Демонстрационный скрипт для работы с параметризованным шаблоном промпта техподдержки.
"""

from langchain_core.prompts import PromptTemplate
from pathlib import Path

def main():
    # Загружаем шаблон из файла
    template_path = Path("support_response_template.txt")
    template_text = template_path.read_text(encoding='utf-8')
    
    # Создаем PromptTemplate из загруженного текста
    support_template = PromptTemplate.from_template(template_text)
    
    # Пример 1: Ответ по технической проблеме
    example1 = support_template.format(
        client_name="Алексей Петров",
        issue_topic="проблема с авторизацией",
        response_body="Мы выявили, что ваша проблема связана с устаревшей версией приложения. "
                     "Пожалуйста, обновите приложение до последней версии 2.5.1, "
                     "это решит проблему с входом в систему.",
        support_agent_name="Мария Сидорова",
        company_name="TechSolutions"
    )
    
    print("Пример 1: Ответ по технической проблеме")
    print("=" * 50)
    print(example1)
    print("\n")
    
    # Пример 2: Ответ по вопросу оплаты
    example2 = support_template.format(
        client_name="Елена Волкова",
        issue_topic="возврат денежных средств",
        response_body="Ваш запрос на возврат был обработан. "
                     "Деньги вернутся на ваш счет в течение 5 рабочих дней. "
                     "Номер транзакции: RFN-789456123.",
        support_agent_name="Дмитрий Иванов",
        company_name="TechSolutions"
    )
    
    print("Пример 2: Ответ по вопросу оплаты")
    print("=" * 50)
    print(example2)
    print("\n")
    
    # Пример 3: Ответ по общему вопросу
    example3 = support_template.format(
        client_name="Иван Смирнов",
        issue_topic="доступ к новым функциям",
        response_body="Новые функции будут доступны всем пользователям "
                     "после обновления системы, запланированного на следующей неделе. "
                     "Вы получите уведомление о доступности обновления.",
        support_agent_name="Анна Кузнецова",
        company_name="TechSolutions"
    )
    
    print("Пример 3: Ответ по общему вопросу")
    print("=" * 50)
    print(example3)
    print("\n")
    
    # Демонстрация использования partial для фиксации общих параметров
    print("Демонстрация частичного заполнения шаблона:")
    print("=" * 50)
    
    # Создаем частично заполненный шаблон с фиксированным агентом и компанией
    partial_template = support_template.partial(
        support_agent_name="Робот Поддержки",
        company_name="TechSolutions"
    )
    
    # Используем частично заполненный шаблон
    partial_example = partial_template.format(
        client_name="Наталья Орлова",
        issue_topic="вопрос по документации",
        response_body="Вы можете найти всю необходимую документацию в разделе 'Помощь' на нашем сайте. "
                     "Также рекомендуем ознакомиться с обучающими материалами в личном кабинете."
    )
    
    print(partial_example)

if __name__ == "__main__":
    main()