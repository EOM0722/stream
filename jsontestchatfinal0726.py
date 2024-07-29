import streamlit as st
from pymongo import MongoClient
from PIL import Image
import base64
import anthropic

# MongoDB 설정
client = MongoClient("mongodb://localhost:27017/")
db = client["books_db"]
books_collection = db["books"]
info_collection = db["info"]

# Anthropic 클라이언트 설정
claude_client = anthropic.Anthropic(api_key=st.secrets["ANTHROPIC_API_KEY"])

# 이미지를 base64로 인코딩
def get_base64_image(image_path):
    with open(image_path, "rb") as image_file:
        return base64.b64encode(image_file.read()).decode()

# 이미지 파일 경로
avatar_image_path = "chat.jpg"
background_image_path = "back.png"

# 이미지 로드
base64_avatar = get_base64_image(avatar_image_path)
base64_background = get_base64_image(background_image_path)

# CSS 스타일
st.markdown(f"""
<style>
    .stApp {{
        background-image: linear-gradient(
            rgba(255, 255, 255, 0.5), 
            rgba(255, 255, 255, 0.5)
        ), url("data:image/png;base64,{base64_background}");
        background-size: cover;
        background-position: center;
    }}
    .chat-container {{
        display: flex;
        align-items: flex-start;
        margin-bottom: 20px;
    }}
    .avatar {{
        width: 150px;
        border-radius: 50%;
        margin-right: 20px;
    }}
    .chat-bubble {{
        background-color: rgba(241, 241, 241, 0.9);
        border-radius: 20px;
        padding: 15px;
        max-width: 70%;
    }}
    .user-input {{
        background-color: rgba(225, 245, 254, 0.9);
        border-radius: 20px;
        padding: 15px;
        max-width: 70%;
        margin-left: auto;
    }}
</style>
""", unsafe_allow_html=True)

st.title("책 및 정보 기반 Claude.ai 챗봇")
st.write("질문을 입력하세요:")

# 세션 상태 초기화
if "messages" not in st.session_state:
    st.session_state.messages = []

# 최대 메시지 수 설정
MAX_MESSAGES = 10

# 아바타와 대화 표시
for message in st.session_state.messages[-MAX_MESSAGES:]:
    if message["role"] == "assistant":
        st.markdown(f"""
        <div class="chat-container">
            <img src="data:image/jpeg;base64,{base64_avatar}" class="avatar">
            <div class="chat-bubble">{message['content']}</div>
        </div>
        """, unsafe_allow_html=True)
    else:
        st.markdown(f"""
        <div class="chat-container">
            <div class="user-input">{message['content']}</div>
        </div>
        """, unsafe_allow_html=True)

# 사용자 입력
user_input = st.text_input("질문을 입력하세요:")

if user_input:
    # 메시지 수가 최대치를 넘으면 오래된 메시지 제거
    if len(st.session_state.messages) >= MAX_MESSAGES:
        st.session_state.messages = st.session_state.messages[-MAX_MESSAGES:]

    st.session_state.messages.append({"role": "user", "content": user_input})
    
    # MongoDB에서 모든 책 정보 가져오기
    books_info = list(books_collection.find())
    info_info = info_collection.find_one()

    # 필요한 부분만 추출하여 combined_info 구성
    combined_info = []
    
    if books_info:
        for book in books_info:
            combined_info.append(f"책 제목: {book['title']}")
            combined_info.append(f"저자: {book['author']}")
            combined_info.append(f"출판일: {book['pub_date']}")
            combined_info.append(f"내용 요약: {book['content'][:1000]}...")  # 요약을 위해 내용 일부만 포함

    if info_info:
        combined_info.append(f"이름: {info_info.get('name', 'N/A')}")
        combined_info.append(f"역할: {info_info.get('role', 'N/A')}")
        combined_info.append(f"재단 소개: {info_info.get('foundation_intro', 'N/A')[:500]}...")  # 요약을 위해 소개 일부만 포함
        if 'history' in info_info:
            combined_info.append("연혁 요약:")
            for history in info_info['history']:
                combined_info.append(f"{history['year']}년: " + ", ".join(history['events'][:2]) + "...")
        if 'team' in info_info:
            combined_info.append("주요 의료진:")
            for team_member in info_info['team'][:3]:  # 요약을 위해 일부 팀원만 포함
                combined_info.append(f"{team_member['name']} - {team_member['role']}")
        if 'locations' in info_info:
            combined_info.append("병원 위치:")
            for location in info_info['locations']:
                combined_info.append(f"{location['name']} - 주소: {location['address']}, 전화: {location['tel']}")
                combined_info.append(f"버스: {', '.join(location['directions']['bus'])}")
                combined_info.append(f"지하철: {location['directions']['subway']}")
                combined_info.append(f"자가용: {location['directions']['car']}")
                combined_info.append(f"운영 시간: 평일 - {location['hours']['weekdays']}, 주말 - {location['hours']['weekends']}, 점심시간 - {location['hours']['lunch']}")

    combined_info_text = "\n".join(combined_info)

    if combined_info_text:
        # AI 응답 생성
        with st.spinner("답변을 작성 중입니다..."):
            prompt = f"Human: 다음 정보를 바탕으로 질문에 답하세요: {combined_info_text}\n\nHuman: {user_input}\n\nAssistant:"
            
            response = claude_client.completions.create(
                model="claude-v1",
                prompt=prompt,
                max_tokens_to_sample=1000
            )
            
            ai_response = response.completion
            st.session_state.messages.append({"role": "assistant", "content": ai_response})

            # 새 메시지 표시
            st.markdown(f"""
            <div class="chat-container">
                <img src="data:image/jpeg;base64,{base64_avatar}" class="avatar">
                <div class="chat-bubble">{ai_response}</div>
            </div>
            """, unsafe_allow_html=True)

# 스크롤을 최신 메시지로 이동
if st.session_state.messages:
    st.markdown("""
        <script>
            var element = document.getElementById('bottom');
            element.scrollIntoView({behavior: "smooth"});
        </script>
    """, unsafe_allow_html=True)
    st.markdown('<div id="bottom"></div>', unsafe_allow_html=True)
