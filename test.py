from config import AI_TOKEN
from openai import OpenAI
import tiktoken

def ai_rewriting(post_text):
    client = OpenAI(api_key=AI_TOKEN)
    encoding = tiktoken.encoding_for_model('gpt-3.5-turbo-instruct')
    prompt = f'Перефразируй текст из данного поста, оставляя эмодзи {post_text}'
    tokens = encoding.encode(prompt)
    print('Tokens: ', len(tokens))
    response = client.completions.create(
        model='gpt-3.5-turbo-instruct',
        prompt=prompt,
        max_tokens=len(tokens)*2
    )
    print(response)
    return response.choices[0].text.strip()

print(ai_rewriting('''🌿 Флорариум в Зарядье, где всегда зелено

Уникальная оранжерея в виде воронки соединяет природу и технологии, просвещение и развлечения, а также историю и современность.'''))