import os
import datetime
import re
import random
from openai import OpenAI

WIKI_IMAGES = [
    "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1581092580497-e0d23cb11b4f?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&h=675&q=80"
]

def get_previous_concepts():
    concepts = []
    if not os.path.exists("_posts"): return concepts
    for filename in os.listdir("_posts"):
        if filename.endswith(".md"):
            with open(os.path.join("_posts", filename), "r", encoding="utf-8") as f:
                content = f.read()
                if "반도체 백과사전" in content:
                    title_match = re.search(r'title:\s*"(.*?)"', content)
                    if title_match:
                        concepts.append(title_match.group(1))
    return concepts[-10:] 

def generate_concept_wiki(previous_topics):
    print("[1/3] 순수 텍스트 기반 위키 문서 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 누락")
        
    client = OpenAI(api_key=api_key)
    prev_topics_str = "\n".join(previous_topics) if previous_topics else "기록 없음."
    
    system_prompt = """
    당신은 화학공학 전공 테크 위키 작성자입니다. 이전 주제와 겹치지 않는 심화 공정 개념 1가지를 정해 매우 상세히(최소 2500자) 작성하세요.
    수식은 반드시 $$ 기호로 감싸고, \mathrm{} 과 \to 를 사용하세요. (예: $$ \mathrm{SiH}_4 \to \mathrm{Si} + 2\mathrm{H}_2 $$)
    절대 본문에 이미지를 임의로 삽입하지 마세요.
    """

    user_prompt = f"""
    반드시 아래의 양식으로만 출력하세요. (JSON 포맷 절대 금지)
    
    Title: [반도체 백과사전] (선정한 주제명)
    Content:
    [서론, 딥다이브 원리(H2, H3 활용), 수식, 결론으로 구성된 마크다운 본문]

    이전 위키 주제 목록:
    {prev_topics_str}
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.5
    )
    
    full_text = response.choices[0].message.content
    try:
        title = re.search(r'Title:\s*(.*)', full_text, re.IGNORECASE).group(1).strip()
        content = re.search(r'Content:\s*(.*)', full_text, re.IGNORECASE | re.DOTALL).group(1).strip()
    except AttributeError:
        title = f"[반도체 백과사전] {datetime.datetime.now().strftime('%m월 %d일')} 새로운 공정 기술"
        content = full_text
        
    return title, content

def inject_html_images(content, image_list):
    lines = content.split('\n')
    new_lines = []
    img_count = 0
    for line in lines:
        new_lines.append(line)
        if line.startswith('## ') and img_count < 2:
            img = random.choice(image_list)
            html_img = f'\n<img src="{img}" alt="공정 원리 참고 이미지" style="width:100%; border-radius:12px; margin: 20px 0;">\n'
            new_lines.append(html_img)
            img_count += 1
    return '\n'.join(new_lines)

def save_to_markdown(title, content):
    print("[2/3] 수식 보호 및 HTML 이미지 주입 중...")
    
    content = content.replace('\\', '\\\\')
    content = inject_html_images(content, WIKI_IMAGES)

    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-wiki-{safe_title}.md"
    if len(filename) > 100:
        filename = f"_posts/{date_str}-wiki-semicon-concept.md"
    
    header_image = random.choice(WIKI_IMAGES)
    
    front_matter = f"""---
title: "{title}"
date: {now.strftime("%Y-%m-%d %H:%M:%S +0900")}
categories: [반도체 백과사전, 공정기술]
tags: [반도체사전, 화학공학, 공정엔지니어]
image:
  path: "{header_image}"
math: true
mermaid: true
---

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    
    print(f"✅ 에러 없는 최종 파일 생성 완료: {filename}")

def main():
    print("=== 기술 백과사전 스크립트 시작 ===")
    prev_topics = get_previous_concepts()
    title, content = generate_concept_wiki(prev_topics)
    save_to_markdown(title, content)
    print("[3/3] 백과사전 로컬 파일 쓰기 완료.")

if __name__ == "__main__":
    main()
