import os
import datetime
import re
import random
import requests
from openai import OpenAI

FALLBACK_IMAGES = ["https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&h=675&q=80"]

def get_dynamic_image(keyword):
    """💡 AI가 지정한 맞춤형 키워드로 관련성 높은 썸네일 검색"""
    api_key = os.environ.get("UNSPLASH_API_KEY")
    if not api_key or not keyword:
        return random.choice(FALLBACK_IMAGES)
    try:
        url = f"https://api.unsplash.com/photos/random?query={keyword}&client_id={api_key}"
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
    print("[1/3] 내용 중심 구조적 위키 문서 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    prev_topics_str = "\n".join(previous_topics) if previous_topics else "기록 없음."
    
    system_prompt = """
    당신은 화학공학 전공 테크 위키 작성자입니다.
    
    [시각화 및 딥다이브 규칙]
    1. 사진(이미지) 삽입은 절대 금지합니다.
    2. 정보량이 방대하게 느껴지도록 텍스트 길이를 최소 4,000자 이상으로 매우 상세히 늘려 쓰세요.
    3. 사진이 없는 대신 기술의 이해를 돕기 위해 아래 시각화 기법을 2~3회 이상 사용하세요.
       - Mermaid 다이어그램: 공정 플로우, 메커니즘을 `mermaid` 코드 블록으로 구조화.
       - 마크다운 표(Table): 화학 물질 특성, 공정 스펙 비교표.
    4. 수식은 LaTeX 금지, HTML 태그(<sub>, <sup>, &rarr;)만 사용하세요.
    """

    user_prompt = f"""
    반드시 아래 양식의 순수 텍스트로만 출력하세요.
    
    Title: [반도체 백과사전] (선정한 주제명만 간결하게)
    Image_Keyword: (주제에 맞는 Unsplash 검색용 영어 단어 1~2개, 예: lithography, etching, chemistry)
    Content:
    [인용구 요약, 딥다이브 원리(Mermaid, 표 적극 활용), 한계 및 전망으로 구성된 본문]

    이전 위키 주제 목록:
    {prev_topics_str}
    
    위 목록과 겹치지 않는 다음 단계의 심화 공정 개념 1가지를 정하여 작성하세요.
    """

    response = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": system_prompt}, {"role": "user", "content": user_prompt}],
        temperature=0.5
    )
    
    full_text = response.choices[0].message.content
    try:
        title = re.search(r'Title:\s*(.*)', full_text, re.IGNORECASE).group(1).strip()
        keyword = re.search(r'Image_Keyword:\s*(.*)', full_text, re.IGNORECASE).group(1).strip()
        content = re.search(r'Content:\s*(.*)', full_text, re.IGNORECASE | re.DOTALL).group(1).strip()
    except:
        title = f"[반도체 백과사전] {datetime.datetime.now().strftime('%m월 %d일')} 공정 딥다이브"
        keyword = "semiconductor manufacturing"
        content = full_text
    
    title = title.replace('[기술위키]', '').strip()
    if not title.startswith("[반도체 백과사전]"):
        title = f"[반도체 백과사전] {title}"
        
    return title, keyword, content

def save_to_markdown(title, keyword, content):
    print(f"[2/3] 맞춤형 썸네일({keyword}) 검색 및 파일 생성 중...")
    
    content = content.replace('\\', '\\\\')
    
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-wiki-{safe_title}.md"
    
    header_image = get_dynamic_image(keyword)
    
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
    title, keyword, content = generate_concept_wiki(prev_topics)
    save_to_markdown(title, keyword, content)

if __name__ == "__main__":
    main()
