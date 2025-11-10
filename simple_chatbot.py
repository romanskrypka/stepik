def solution():
    # ==== Ваш код тут ====
    # Импорты уже выполнены в среде, поэтому не нужно их повторять
    
    # Создаем агента с памятью
    agent = create_agent(
        model="gpt-5",
        checkpointer=InMemorySaver()
    )
    
    # Конфигурация для сохранения контекста
    config = {"configurable": {"thread_id": "conversation_1"}}
    
    # Цикл диалога
    while True:
        # Считываем ввод пользователя
        user_input = input().strip()
        
        # Проверяем, хочет ли пользователь выйти
        if user_input.lower() == "выход":
            print("До свидания!")
            break
        
        # Отправляем запрос агенту
        response = agent.invoke(
            {"messages": [{"role": "user", "content": user_input}]},
            config
        )
        
        # Выводим ответ агента
        print(response["messages"][-1].content)