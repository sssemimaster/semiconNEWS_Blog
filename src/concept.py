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
    "https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1611078518653-568853b0bcce?auto=format&fit=crop&w=1200&h=675&q=80"
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
        raise ValueError("OPENAI_API_KEY 환경 변수가 누락되었습니다.")
        
    client = OpenAI(api_key=api_key)
    prev_topics_str = "\n".join(previous_topics) if previous_topics else "기록 없음. '반도체 8대 공정 전체 개요'부터 시작하세요."
    image_pool_str = "\n".join([f"- {img}" for img in WIKI_IMAGES])
    
    system_prompt = """
    당신은 화학공학 전공 반도체 엔지니어이자 테크 위키 작성자입니다.
    이전 주제 목록을 분석하여 중복되지 않는 다음 단계의 심화 공정 개념 1가지를 선정하고, 최소 2500자 이상의 문서를 작성하세요.

    [화학 반응식 필수 작성 가이드]
    1. 수식을 작성할 때는 무조건 `$$` 기호로 감싸세요. (예: `$$ \mathrm{SiH}_4 \to \mathrm{Si} + 2\mathrm{H}_2 $$`)
    2. 블로그 에러를 막기 위해 화학 물질명은 `\text{}` 대신 `\mathrm{}`을 사용하세요.
    """

    user_prompt = f"""
    [이전 위키 주제 목록]
    {prev_topics_str}

    [이미지 자동 삽입 가이드]
    본문 설명 중간중간 아래 제공된 URL 중 1~2개를 골라 정확히 복사하여 `![이미지 설명](URL)` 마크다운 형식으로 삽입하세요.
    {image_pool_str}

    위 목록을 참고하여 오늘 작성할 1개의 핵심 개념을 스스로 정하고, JSON 형식으로 응답하세요.
    키는 "concept_title" (기술명), "title" (블로그 제목, "[반도체 백과사전] ~" 형태), "content" (완벽한 마크다운 본문) 세 개입니다.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.6,
        response_format={"type": "json_object"}
    )
    
    post_data = json.loads(response.choices[0].message.content)
    return post_data['title'], post_data['content']

def save_to_markdown(title, content):
    print("[2/3] 백과사전 마크다운 파일 생성 및 교정 중...")
    
    # 💡 [핵심 안전장치] AI가 잘못 생성한 수식 기호를 블로그 호환(MathJax) 기호로 강제 치환
    content = content.replace('\\[', '$$').replace('\\]', '$$')
    content = content.replace('\[', '$$').replace('\]', '$$')
    content = content.replace('\\text{', '\\mathrm{')
    
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
tags: [반도체사전, 화학공학, 공정엔지니어, 테크위키]
image:
  path: "{header_image}"
math: true
mermaid: true
---

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    
    print(f"✅ 교정 완료 및 파일 생성: {filename}")

def main():
    print("=== 반도체 기술 백과사전 자동화 시작 ===")
    prev_topics = get_previous_concepts()
    title, content = generate_concept_wiki(prev_topics)
    save_to_markdown(title, content)
    print("[3/3] 백과사전 로컬 파일 쓰기 완료.")

if __name__ == "__main__":
    main()
