import os
import datetime
import json
import re
import random
from openai import OpenAI

# 백과사전에 어울리는 연구실, 웨이퍼, 팹 내부 고화질 이미지
WIKI_IMAGES = [
    "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1581092580497-e0d23cb11b4f?auto=format&fit=crop&w=1200&q=80",
    "https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&q=80"
]

def get_previous_concepts():
    """이전에 작성된 백과사전 주제들을 읽어와 중복을 방지하고 다음 진도를 파악합니다."""
    concepts = []
    if not os.path.exists("_posts"):
        return concepts
        
    for filename in os.listdir("_posts"):
        if filename.endswith(".md"):
            with open(os.path.join("_posts", filename), "r", encoding="utf-8") as f:
                content = f.read()
                if "반도체 백과사전" in content:
                    # 파일명에서 날짜 부분 제외하고 제목만 추출
                    title_match = re.search(r'title:\s*"(.*?)"', content)
                    if title_match:
                        concepts.append(title_match.group(1))
    return concepts[-15:] # 가장 최근 15개 주제만 전달하여 문맥 유지

def generate_concept_wiki(previous_topics):
    print("[1/3] OpenAI로 다음 반도체 기술 개념 및 본문 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 환경 변수가 설정되지 않았습니다.")
        
    client = OpenAI(api_key=api_key)
    today_str = datetime.datetime.now().strftime("%Y년 %m월 %d일")
    
    prev_topics_str = "\n".join(previous_topics) if previous_topics else "아직 작성된 문서가 없습니다. 가장 기초적인 '반도체 8대 공정 개요'부터 시작하세요."
    
    system_prompt = """
    당신은 화학공학을 전공한 반도체 공정 엔지니어이자, 나무위키/노션 스타일의 테크 위키 작성자입니다.
    이전에 작성된 주제 목록을 분석하여, 논리적으로 이어지는 **다음 단계의 심화/세부 반도체 기술 개념 1가지**를 스스로 선정하고 완벽한 위키 문서를 작성하세요.

    [주제 선정 알고리즘]
    - 이전 주제가 넓은 범위(예: 포토공정)였다면, 오늘은 세부 화학/물리 원리(예: EUV 광원의 원리 또는 PR의 화학 구조)로 딥다이브하세요.
    - 너무 한쪽 공정에 치우쳤다면 다른 핵심 공정(식각, 증착, 세정, 패키징 등)이나 핵심 소재(특수가스, 전구체 등)로 자연스럽게 넘어가세요.

    [위키 마크다운 서식 가이드]
    1. **노션 스타일 요약 (콜아웃)**: 서론은 `> **💡 핵심 요약**` 형태의 인용구 안에 3줄로 명확히 정리하세요.
    2. **화공학적 딥다이브**: 반응식, 열역학적 특성, 유체 흐름, 물질의 화학적 한계 등 공학적 디테일을 반드시 포함하세요. 
    3. **나무위키식 목차 구조**: H2(`##`), H3(`###`)를 체계적으로 사용하여 가독성을 극대화하세요.
    4. **핵심 키워드 볼드체**: 중요한 용어는 **굵은 글씨** 처리하세요.
    """

    user_prompt = f"""
    [이전까지 작성된 위키 주제 목록]
    {prev_topics_str}

    위 목록을 참고하여 오늘 작성할 단 1개의 핵심 개념을 스스로 정하고, JSON 형식으로 응답하세요.
    키는 "concept_title" (선정한 기술명), "title" (블로그 포스팅용 제목, "[반도체 백과사전] ~" 형태), "content" (완벽한 마크다운 본문) 세 개입니다.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        temperature=0.3,
        response_format={"type": "json_object"}
    )
    
    post_data = json.loads(response.choices[0].message.content)
    return post_data['title'], post_data['content']

def save_to_markdown(title, content):
    print("[2/3] 백과사전 마크다운 파일 생성 중...")
    now = datetime.datetime.now()
    
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-wiki-{safe_title}.md"
    
    # 파일명이 너무 길면 자르기
    if len(filename) > 100:
        filename = f"_posts/{date_str}-wiki-semicon-concept.md"
    
    header_image = random.choice(WIKI_IMAGES)
    
    # 백과사전 전용 카테고리 구성
    front_matter = f"""---
title: "{title}"
date: {now.strftime("%Y-%m-%d %H:%M:%S +0900")}
categories: [반도체 백과사전, 공정기술]
tags: [반도체사전, 화학공학, 공정엔지니어, 테크위키]
image:
  path: {header_image}
math: true
mermaid: true
---

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    
    print(f"✅ 위키 문서 생성 완료: {filename}")

def main():
    print("=== 반도체 기술 백과사전 자동화 시작 ===")
    prev_topics = get_previous_concepts()
    title, content = generate_concept_wiki(prev_topics)
    save_to_markdown(title, content)
    print("[3/3] 백과사전 로컬 파일 쓰기 완료.")

if __name__ == "__main__":
    main()
