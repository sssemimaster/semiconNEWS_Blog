import os
import datetime
import re
import random
import requests
from openai import OpenAI

FALLBACK_IMAGES = [
    "https://images.unsplash.com/photo-1581091226825-a6a2a5aee158?auto=format&fit=crop&w=1200&h=675&q=80",
    "https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&h=675&q=80"
]

def get_dynamic_image():
    """💡 Unsplash API 연동 함수"""
    api_key = os.environ.get("UNSPLASH_API_KEY")
    if not api_key:
        return random.choice(FALLBACK_IMAGES)
    
    queries = ["silicon wafer", "nanotechnology", "chemistry lab", "cleanroom", "semiconductor manufacturing"]
    query = random.choice(queries)
    
    try:
        url = f"https://api.unsplash.com/photos/random?query={query}&client_id={api_key}"
        res = requests.get(url, timeout=5)
        res.raise_for_status()
        data = res.json()
        return data['urls']['raw'] + "&w=1200&h=675&fit=crop&q=80"
    except:
        return random.choice(FALLBACK_IMAGES)

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
    
    [위키 템플릿 - 반드시 이 목차 구조를 따를 것]
    ## 1. 개념 개요 (Overview)
    ## 2. 핵심 작동 원리 (Mechanism) - 반드시 Mermaid 다이어그램 포함
    ## 3. 공정 파라미터 및 주요 소재 (Materials & Variables) - 표 포함
    ## 4. 한계점 및 최신 기술 동향 (Trends)

    [규칙]
    1. 사진(이미지) 삽입 절대 금지.
    2. 수식은 LaTeX 절대 금지. HTML 태그(<sub>, <sup>, &rarr;)만 사용.
    3. 최소 3000자 이상의 매우 상세한 딥다이브 문서를 작성하세요.
    """

    user_prompt = f"""
    반드시 아래 양식의 순수 텍스트로만 출력하세요.
    
    Title: [반도체 백과사전] (선정한 주제명만 간결하게)
    Content:
    [템플릿에 맞춘 본문]

    이전 주제 목록:
    {prev_topics_str}
    
    위 목록과 겹치지 않는 다음 단계의 개념 1가지를 정하여 작성하세요.
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
    except:
        title = f"[반도체 백과사전] {datetime.datetime.now().strftime('%m월 %d일')} 공정 딥다이브"
        content = full_text
    
    title = title.replace('[기술위키]', '').strip()
    if not title.startswith("[반도체 백과사전]"):
        title = f"[반도체 백과사전] {title}"
        
    return title, content

def inject_html_images(content):
    lines = content.split('\n')
    new_lines = []
    img_count = 0
    for line in lines:
        new_lines.append(line)
        if line.startswith('## ') and img_count < 2:
            img = get_dynamic_image()
            html_img = f'\n<img src="{img}" alt="공정 딥다이브 자료" style="width:100%; border-radius:12px; margin: 20px 0;">\n'
            new_lines.append(html_img)
            img_count += 1
    return '\n'.join(new_lines)

def save_to_markdown(title, content):
    print("[2/3] 마크다운 파일(시리즈 연동) 생성 중...")
    
    content = content.replace('\\', '\\\\')
    content = inject_html_images(content)
    
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-wiki-{safe_title}.md"
    
    header_image = get_dynamic_image()
    
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
