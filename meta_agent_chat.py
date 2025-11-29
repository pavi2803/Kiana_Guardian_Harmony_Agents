def meta_agent():
    import streamlit as st
    from llama_cpp import Llama
    import google.generativeai as genai

    # Load the model (use your downloaded GGUF path)
    # llm = Llama(model_path="/Users/pavithrasenthilkumar/.cache/huggingface/hub/models--TheBloke--TinyLlama-1.1B-Chat-v1.0-GGUF/snapshots/52e7645ba7c309695bec7ac98f4f005b139cf465/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf", n_ctx=512)
    llm = Llama(model_path="./models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf", n_ctx=512)

    # Initialize session state for chat history
    if "messages" not in st.session_state:
        st.session_state.messages = []

    st.markdown("<h2 style='color:#000000; text-align:center;'> Meta Agent - What's on your mind?</h2>", unsafe_allow_html=True)

    # Display chat messages
    for msg in st.session_state.messages:
        with st.chat_message(msg["role"]):
            st.markdown(msg["content"])

    # User input
    if user_input := st.chat_input("Type your message here..."):
        st.session_state.messages.append({"role": "user", "content": user_input})
        
        # Prepare conversation prompt for TinyLlama
        conversation_text = ""
        for m in st.session_state.messages:
            if m["role"] == "user": 
                conversation_text += f"### Instruction:\n{m['content']}\n### Response:\n"
            else:
                conversation_text += f"{m['content']}\n"

        # Call model
        output = llm(prompt=conversation_text, max_tokens=200)
        bot_reply = output['choices'][0]['text'].strip()

        # Add model reply to chat history
        st.session_state.messages.append({"role": "assistant", "content": bot_reply})
        
        # Display bot reply
        with st.chat_message("assistant"):
            st.markdown(bot_reply)

meta_agent()