// 서버(apps/site/views.py의 _CHAT_MAX_MESSAGE_LENGTH)와 동일한 제한. 초과 시 요청 자체를
// 보내지 않아 rate limit(분당 5회) 슬롯을 실패가 확정된 요청에 낭비하지 않는다.
const MAX_MESSAGE_LENGTH = 2000;

// 대화 기록이 없을 때(최초 진입, 초기화 직후) 보여줄 인사말과 추천 질문.
const GREETING_MESSAGE = '안녕하세요! Chuseok22 AI 챗봇입니다. 무엇을 도와드릴까요?';
const SUGGESTED_QUESTIONS = [
  '기술 스택이 궁금해요',
  '진행한 프로젝트를 소개해줘',
  '블로그에 어떤 글이 있나요?',
  '경력이 궁금해요',
];

function chatbotWidget() {
  return {
    open: false,
    input: '',
    loading: false,
    messages: [],
    greeting: GREETING_MESSAGE,
    suggestedQuestions: SUGGESTED_QUESTIONS,

    init() {
      const saved = sessionStorage.getItem('chatbot-messages');
      if (!saved) return;
      try {
        this.messages = JSON.parse(saved);
      } catch (error) {
        this.messages = [];
      }
    },

    reset() {
      this.messages = [];
      sessionStorage.removeItem('chatbot-messages');
    },

    persist() {
      sessionStorage.setItem('chatbot-messages', JSON.stringify(this.messages));
    },

    async send(presetMessage) {
      const message = (presetMessage ?? this.input).trim();
      if (!message || this.loading) return;

      // 서버는 Python len()으로 유니코드 코드포인트 수를 센다. message.length는 UTF-16 코드
      // 유닛 수라 서로게이트 페어(이모지 등)에서 서버 기준보다 커지므로, [...message].length로
      // 코드포인트 단위로 맞춰 세야 정상 메시지가 잘못 차단되지 않는다.
      if ([...message].length > MAX_MESSAGE_LENGTH) {
        this.messages.push({ role: 'assistant', content: '메시지가 너무 깁니다.', links: [] });
        this.persist();
        return;
      }

      // 서버가 history 항목 수를 20개로 제한하므로(_CHAT_MAX_HISTORY_ITEMS), sessionStorage에
      // 누적된 전체 messages를 그대로 보내면 대화가 길어질수록 400으로 거부된다. 최근 20개만 전송한다.
      const history = this.messages.slice(-20).map((item) => ({ role: item.role, content: item.content }));
      this.messages.push({ role: 'user', content: message });
      // 추천 질문(preset) 클릭은 입력창을 거치지 않으므로, 작성 중이던 초안이 지워지지 않도록
      // 실제 입력 필드에서 보낸 경우(presetMessage === undefined)에만 input을 비운다.
      if (presetMessage === undefined) this.input = '';
      this.loading = true;
      this.persist();
      this.scrollToBottom();

      try {
        const response = await fetch('/chat/', {
          method: 'POST',
          headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCsrfToken(),
          },
          body: JSON.stringify({ message, history }),
        });
        const data = await response.json();
        this.messages.push({
          role: 'assistant',
          content: response.ok ? data.reply : (data.error || '오류가 발생했습니다.'),
          links: response.ok ? (data.links || []) : [],
        });
      } catch (error) {
        this.messages.push({ role: 'assistant', content: '네트워크 오류가 발생했습니다.', links: [] });
      } finally {
        this.loading = false;
        this.persist();
        this.scrollToBottom();
      }
    },

    scrollToBottom() {
      this.$nextTick(() => {
        const list = this.$refs.messageList;
        if (list) list.scrollTop = list.scrollHeight;
      });
    },
  };
}

function getCsrfToken() {
  // base.html의 <meta name="csrf-token"> 태그에서 직접 읽는다. hx-headers 등 다른 기능의
  // 부수효과(쿠키 설정)에 의존하지 않는, 챗봇 위젯 전용의 명시적인 의존성이다.
  const meta = document.querySelector('meta[name="csrf-token"]');
  return meta ? meta.getAttribute('content') : '';
}
