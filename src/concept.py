import os
import datetime
import re
import json
import random
import requests
from openai import OpenAI

FALLBACK_IMAGES = ["https://images.unsplash.com/photo-1531297484001-80022131f5a1?auto=format&fit=crop&w=1200&h=675&q=80"]

def get_dynamic_image(keyword):
    """💡 Unsplash API 연동 (검색어 기반)"""
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
    concepts = set() 
    if not os.path.exists("_posts"): return []
    for filename in os.listdir("_posts"):
        if filename.endswith(".md"):
            with open(os.path.join("_posts", filename), "r", encoding="utf-8") as f:
                content = f.read()
                if "series: 반도체 핵심 공정 백과사전" in content:
                    title_match = re.search(r'title:\s*"(.*?)"', content)
                    if title_match:
                        clean_title = title_match.group(1).replace("[반도체 백과사전]", "").strip()
                        concepts.add(clean_title)
    return list(concepts)

def inject_html_images(content, base_keyword):
    """💡 본문 H2(##) 태그 아래에 이미지를 딱 2장만 삽입합니다."""
    lines = content.split('\n')
    new_lines = []
    img_count = 0
    # 본문 이미지들이 똑같지 않게 검색어에 약간의 변형을 줍니다.
    sub_keywords = ["technology", "process engineering"] 
    
    for line in lines:
        new_lines.append(line)
        if line.startswith('## ') and img_count < 2:
            search_kw = f"{base_keyword} {sub_keywords[img_count]}"
            img = get_dynamic_image(search_kw)
            html_img = f'\n<img src="{img}" alt="공정 시각화 자료" style="width:100%; border-radius:12px; margin: 20px 0;">\n'
            new_lines.append(html_img)
            img_count += 1
    return '\n'.join(new_lines)

def generate_concept_wiki(previous_topics):
    api_key = os.environ.get("OPENAI_API_KEY")
    client = OpenAI(api_key=api_key)
    prev_topics_str = "\n".join([f"- {t}" for t in previous_topics]) if previous_topics else "기록 없음."
    
    print("[1/4] STEP 1: 새로운 주제 선정 및 3단 뼈대(Outline) 기획 중...")
    outline_system = "당신은 화학공학 전공 테크 위키 수석 에디터입니다."
    outline_user = f"""
    [🚨 이미 작성된 주제 목록 - 중복/동의어 절대 금지]
    {prev_topics_str}
    
    위 목록에 없는 '새로운 반도체 심화 공정 개념' 1가지를 선정하여 JSON으로 출력하세요.
    (분량을 줄이기 위해 목차는 딱 3개로 압축합니다.)
    
    {{
        "title": "주제명 (예: 원자층 증착(ALD) 공정)",
        "keyword": "썸네일용 영문 검색어 1개 (예: semiconductor)",
        "outline": [
            "1. 개념 개요 및 핵심 메커니즘",
            "2. 주요 소재 및 공정 파라미터",
            "3. 기술적 한계점 및 향후 전망"
        ]
    }}
    """
    
    res_outline = client.chat.completions.create(
        model="gpt-4o-mini",
        messages=[{"role": "system", "content": outline_system}, {"role": "user", "content": outline_user}],
        response_format={"type": "json_object"},
        temperature=0.6
    )
    
    plan = json.loads(res_outline.choices[0].message.content)
    clean_title = plan["title"]
    final_title = f"[반도체 백과사전] {clean_title}"
    keyword = plan["keyword"]
    sections = plan["outline"]
    
    print(f"[2/4] STEP 2: '{clean_title}' 3단 분할 작성 시작...")
    full_content = ""
    
    # 💡 [핵심] '결론병'을 치료하기 위한 강력한 금지어 설정
    writer_system = """
    당신은 화학공학 전공 시니어 반도체 공정 엔지니어입니다.
    [규칙]
    1. 수식은 LaTeX 금지, HTML 태그(<sub>, <sup>, &rarr;)만 사용.
    2. 내용 중 마크다운 표(Table)와 Mermaid 다이어그램을 활용하세요.
    3. 사진(이미지) 삽입은 절대 금지합니다 (시스템이 나중에 넣습니다).
    4. 🚨 절대 금지어: '결론적으로', '요약하자면', '종합하면', '이처럼'. 이 단어들은 글을 끊어지게 만드므로 절대 쓰지 마세요.
    """

    for i, section_title in enumerate(sections):
        print(f"  -> ({i+1}/{len(sections)}) '{section_title}' 작성 중...")
        
        if i == 0:
            role_guide = "이 부분은 위키의 '개요와 원리'입니다. 절대 결론을 내거나 요약하며 끝맺지 말고 사실만 나열하세요."
        elif i == len(sections) - 1:
            role_guide = "이 부분은 위키의 '한계와 전망'입니다. 앞의 내용을 굳이 요약하지 말고 앞으로의 기술 방향만 제시하며 마무리하세요."
        else:
            role_guide = "이 부분은 위키의 '본론'입니다. 절대 서론이나 결론을 작성하지 마세요. 사실 기반의 데이터와 공정 스펙만 깊게 파고드세요."

        writer_user = f"""
        전체 위키 주제: {clean_title}
        현재 작성할 섹션: ## {section_title}
        작성 지침: {role_guide}
        
        [지금까지 작성된 앞부분 내용]
        {full_content if full_content else "없음 (이제 시작함)"}
        
        위 앞부분 내용과 물 흐르듯 자연스럽게 이어지도록, 현재 섹션에 해당하는 내용만 전문적으로 작성하세요.
        """
        
        res_section = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[{"role": "system", "content": writer_system}, {"role": "user", "content": writer_user}],
            temperature=0.5
        )
        
        section_content = res_section.choices[0].message.content.strip()
        full_content += f"## {section_title}\n\n{section_content}\n\n---\n\n"

    return final_title, keyword, full_content

def save_to_markdown(title, keyword, content):
    print(f"[3/4] 썸네일 및 본문 이미지 2장 주입 중...")
    content = content.replace('\\', '\\\\')
    
    # 💡 본문에 이미지 2개 삽입
    content = inject_html_images(content, keyword)
    
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

> **💡 {title.replace('[반도체 백과사전]', '').strip()}에 대한 심층 딥다이브 문서입니다.**

"""
    os.makedirs("_posts", exist_ok=True)
    with open(filename, "w", encoding="utf-8") as f:
        f.write(front_matter + content)
    print(f"[4/4] ✅ 백과사전 파일 생성 완료: {title}")

def main():
    print("=== 위키 다중 생성 자동화 시작 ===")
    prev_topics = get_previous_concepts()
    title, keyword, content = generate_concept_wiki(prev_topics)
    save_to_markdown(title, keyword, content)

if __name__ == "__main__":
    main()
