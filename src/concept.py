import os
import datetime
import json
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
    if not os.path.exists("_posts"):
        return concepts
    for filename in os.listdir("_posts"):
        if filename.endswith(".md"):
            with open(os.path.join("_posts", filename), "r", encoding="utf-8") as f:
                content = f.read()
                if "반도체 백과사전" in content:
                    title_match = re.search(r'title:\s*"(.*?)"', content)
                    if title_match:
                        concepts.append(title_match.group(1))
    return concepts[-15:] 

def generate_concept_wiki(previous_topics):
    print("[1/3] OpenAI 위키 문서 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 누락")
        
    client = OpenAI(api_key=api_key)
    prev_topics_str = "\n".join(previous_topics) if previous_topics else "기록 없음."
    
    system_prompt = """
    당신은 화학공학 전공 반도체 엔지니어이자 테크 위키 작성자입니다.

    [화학 반응식 절대 규칙 - 위반 시 시스템 붕괴]
    1. LaTeX 기호(`$$`, `\text`, `\rightarrow`)를 **절대 사용하지 마세요.**
    2. 무조건 **HTML 태그**를 사용하여 화학식을 작성하세요.
       - 아래첨자: `<sub>` (예: `SiH<sub>4</sub>`)
       - 위첨자: `<sup>` (예: `O<sup>2-</sup>`)
       - 화살표: `&rarr;` (예: `SiH<sub>4</sub> &rarr; Si + 2H<sub>2</sub>`)
    3. 본문에 이미지를 임의로 삽입하지 마세요. (시스템이 자동으로 삽입합니다)
    """

    user_prompt = f"""
    [이전 위키 주제 목록]
    {prev_topics_str}

    위 목록과 겹치지 않는 다음 단계의 심화 공정 개념 1가지를 정하고 JSON으로 응답하세요.
    (키: "concept_title", "title", "content")
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.5,
        response_format={"type": "json_object"}
    )
    
    post_data = json.loads(response.choices[0].message.content)
    return post_data['title'], post_data['content']

def inject_images_deterministically(content, image_list):
    content = re.sub(r'!\[.*?\]\(.*?\)', '', content)
    lines = content.split('\n')
    new_lines = []
    inserted_count = 0
    for line in lines:
        new_lines.append(line)
        if line.startswith('## ') and inserted_count < 2:
            img = random.choice(image_list)
            new_lines.append(f"\n![공정 참고 자료]({img})\n")
            inserted_count += 1
    return '\n'.join(new_lines)

def save_to_markdown(title, content):
    print("[2/3] 백과사전 이미지 주입 및 파일 생성 중...")
    
    content = inject_images_deterministically(content, WIKI_IMAGES)

    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-wiki-{safe_title}.md"
    if len(filename) > 100:
        filename = f"_posts/{date_str}-wiki-semicon-concept.md"
    
    header_image = random.choice(WIKI_IMAGES)
    
    css_injection = """
<style>
  .post-content img, .preview-img img, .post-header img {
    object-fit: contain !important;
    background-color: transparent !important;
  }
</style>
"""

    front_matter = f"""---
title: "{title}"
date: {now.strftime("%Y-%m-%d %H:%M:%S +0900")}
categories: [반도체 백과사전, 공정기술]
tags: [반도체사전, 화학공학, 공정엔지니어, 테크위키]
image:
  path: "{header_image}"
math: true
mermaid: true
---
{css_injection}
"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    
    print(f"✅ 파일 생성 완료: {filename}")

def main():
    print("=== 반도체 기술 백과사전 자동화 시작 ===")
    prev_topics = get_previous_concepts()
    title, content = generate_concept_wiki(prev_topics)
    save_to_markdown(title, content)
    print("[3/3] 백과사전 로컬 파일 쓰기 완료.")

if __name__ == "__main__":
    main()
