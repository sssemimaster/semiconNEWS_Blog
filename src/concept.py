import os
import datetime
import re
import random
from openai import OpenAI

HEADER_IMAGES = [
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
    print("[1/3] 위키 문서 (시각화 기법 포함) 생성 중...")
    api_key = os.environ.get("OPENAI_API_KEY")
    if not api_key:
        raise ValueError("OPENAI_API_KEY 누락")
        
    client = OpenAI(api_key=api_key)
    prev_topics_str = "\n".join(previous_topics) if previous_topics else "기록 없음."
    
    system_prompt = """
    당신은 화학공학 전공 테크 위키 작성자입니다.
    
    [시각화 및 딥다이브 규칙]
    1. 사진(이미지) URL 삽입은 절대 금지합니다.
    2. 기술의 이해를 돕기 위해 본문 중간중간 다양한 시각화 기법을 사용하세요.
       - Mermaid 다이어그램: 플로우차트, 상태도 등을 사용해 반응 메커니즘이나 장비 구조를 시각화하세요. (`mermaid` 코드 블록 사용)
       - 마크다운 표(Table): 파라미터 비교, 물질 특성 등을 표로 정리하세요.
       - 단계별 리스트: 공정 순서를 넘버링(1, 2, 3)하여 체계적으로 설명하세요.
    3. 수식은 LaTeX(백슬래시)를 절대 쓰지 말고, HTML 태그(<sub>, <sup>, &rarr;)만 사용하세요.
    4. 위키답게 매우 구조적이고 정보량이 방대하게(최소 3000자 이상) 작성하세요.
    """

    user_prompt = f"""
    반드시 아래 양식의 순수 텍스트로만 출력하세요. (JSON 포맷 절대 금지)
    
    Title: [반도체 백과사전] (선정한 주제명)
    Content:
    [인용구 요약, 딥다이브 원리(Mermaid 다이어그램, 표 활용), 결론으로 구성된 마크다운 본문]

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
        content = re.search(r'Content:\s*(.*)', full_text, re.IGNORECASE | re.DOTALL).group(1).strip()
    except AttributeError:
        title = f"[반도체 백과사전] {datetime.datetime.now().strftime('%m월 %d일')} 딥다이브"
        content = full_text
        
    return title, content

def save_to_markdown(title, content):
    print("[2/3] 마크다운 파일 생성 중...")
    
    now = datetime.datetime.now()
    date_str = now.strftime("%Y-%m-%d")
    safe_title = re.sub(r'[^가-힣A-Za-z0-9\s]', '', title).strip().replace(' ', '-')
    filename = f"_posts/{date_str}-wiki-{safe_title}.md"
    if len(filename) > 100:
        filename = f"_posts/{date_str}-wiki-semicon-concept.md"
    
    header_image = random.choice(HEADER_IMAGES)
    
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
    
    print(f"✅ 파일 생성 완료: {filename}")

def main():
    print("=== 기술 백과사전 스크립트 시작 ===")
    prev_topics = get_previous_concepts()
    title, content = generate_concept_wiki(prev_topics)
    save_to_markdown(title, content)
    print("=== 자동화 완료 ===")

if __name__ == "__main__":
    main()
