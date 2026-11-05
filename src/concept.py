import os
import datetime
import re
import random
from openai import OpenAI

# 💡 고화질 반도체/연구실 이미지 풀 확장
HEADER_IMAGES = [
    "https://images.unsplash.com/photo-1611078518653-568853b0bcce?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1518770660439-4636190af475?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1581092160562-40aa08e78837?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1563770660941-20978e870e26?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1581092580497-e0d23cb11b4f?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1581092160607-ee22621dd758?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1517077304055-6e89abbf09b0?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1550751827-4bd374c3f58b?auto=format&fit=crop&w=1200&h=675&q=80"
]

def get_previous_concepts():
    concepts = []
    if not os.path.exists("_posts"): return concepts
    for filename in os.listdir("_posts"):
        if filename.endswith(".md"):
            with open(os.path.join("_posts", filename), "r", encoding="utf-8") as f:
                content = f.read()
                if "series: 반도체 핵심 공정 백과사전" in content:
                    title_match = re.search(r'title:\s*"(.*?)"', content)
                    if title_match:
                        concepts.append(title_match.group(1))
    return concepts[-15:] 

def generate_concept_wiki(previous_topics):
    print("[1/3] 구조적 위키 문서 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    prev_topics_str = "\n".join(previous_topics) if previous_topics else "기록 없음."
    
    system_prompt = """
    당신은 화학공학 전공 테크 위키 작성자입니다.
    글을 읽는 독자가 나무위키의 잘 정리된 기술 위키를 보는 것처럼 느끼도록 체계적으로 구조화된 글을 쓰세요.
    
    [위키 템플릿 - 반드시 이 목차 구조를 따를 것]
    ## 1. 개념 개요 (Overview)
    ## 2. 핵심 작동 원리 (Mechanism) - 반드시 Mermaid 다이어그램 포함
    ## 3. 공정 파라미터 및 주요 소재 (Materials & Variables) - 반드시 마크다운 표(Table) 포함
    ## 4. 한계점 및 최신 기술 동향 (Trends & Challenges)

    [규칙]
    1. 사진(이미지) 삽입 절대 금지.
    2. 수식은 LaTeX(백슬래시) 절대 금지. HTML 태그(<sub>, <sup>, &rarr;)만 사용.
    3. 최소 3000자 이상의 매우 상세한 딥다이브 문서를 작성하세요.
    """

    user_prompt = f"""
    반드시 아래 양식의 순수 텍스트로만 출력하세요.
    
    Title: [반도체 백과사전] (선정한 주제명만 간결하게)
    Content:
    [제시된 위키 템플릿에 맞춘 마크다운 본문]

    이전 위키 주제 목록:
    {prev_topics_str}
    
    위 목록과 겹치지 않는 다음 단계의 심화 공정 개념 1가지를 정하여 작성하세요.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.4
    )
    
    full_text = response.choices[0].message.content
    try:
        title = re.search(r'Title:\s*(.*)', full_text, re.IGNORECASE).group(1).strip()
        content = re.search(r'Content:\s*(.*)', full_text, re.IGNORECASE | re.DOTALL).group(1).strip()
    except AttributeError:
        title = f"[반도체 백과사전] {datetime.datetime.now().strftime('%m월 %d일')} 반도체 공정 딥다이브"
        content = full_text
    
    title = title.replace('[기술위키]', '').strip()
    if not title.startswith("[반도체 백과사전]"):
        title = f"[반도체 백과사전] {title}"
        
    return title, content

def get_unique_image(image_pool):
    """💡 최근 작성된 글 10개의 썸네일을 분석하여 겹치지 않는 이미지를 반환합니다."""
    used_images = []
    if os.path.exists("_posts"):
        files = sorted(os.listdir("_posts"), reverse=True)[:10]
        for filename in files:
            if filename.endswith(".md"):
                with open(os.path.join("_posts", filename), "r", encoding="utf-8") as f:
                    content = f.read()
                    match = re.search(r'image:\s*path:\s*"(.*?)"', content)
                    if match:
                        used_images.append(match.group(1))
    
    available_images = [img for img in image_pool if img not in used_images]
    if not available_images:
        available_images = image_pool
        
    return random.choice(available_images)

def save_to_markdown(title, content):
    print("[2/3] 마크다운 파일(시리즈 연동) 생성 중...")
    
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-wiki-{safe_title}.md"
    
    # 💡 겹치지 않는 썸네일 이미지 자동 추출
    header_image = get_unique_image(HEADER_IMAGES)
    
    front_matter = f"""---
title: "{title}"
date: {now.strftime("%Y-%m-%d %H:%M:%S +0900")}
categories: [반도체 백과사전, 공정기술]
tags: [반도체위키, 8대공정, 딥다이브]
series: 반도체 핵심 공정 백과사전
image:
  path: "{header_image}"
math: true
mermaid: true
---

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    
    print(f"✅ 위키 파일 생성 완료")

def main():
    print("=== 위키 스크립트 시작 ===")
    prev_topics = get_previous_concepts()
    title, content = generate_concept_wiki(prev_topics)
    save_to_markdown(title, content)

if __name__ == "__main__":
    main()
