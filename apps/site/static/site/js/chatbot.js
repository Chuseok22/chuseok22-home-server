// 서버(apps/site/views.py의 _CHAT_MAX_MESSAGE_LENGTH)와 동일한 제한. 초과 시 요청 자체를
// 보내지 않아 rate limit(분당 5회) 슬롯을 실패가 확정된 요청에 낭비하지 않는다.
const MAX_MESSAGE_LENGTH = 2000;

function chatbotWidget() {
  return {
    open: false,
    input: '',
    loading: false,
    messages: [],

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

    async send() {
      const message = this.input.trim();
      if (!message || this.loading) return;

      if (message.length > MAX_MESSAGE_LENGTH) {
        this.messages.push({ role: 'assistant', content: '메시지가 너무 깁니다.' });
        this.persist();
        return;
      }

      // 서버가 history 항목 수를 20개로 제한하므로(_CHAT_MAX_HISTORY_ITEMS), sessionStorage에
      // 누적된 전체 messages를 그대로 보내면 대화가 길어질수록 400으로 거부된다. 최근 20개만 전송한다.
      const history = this.messages.slice(-20).map((item) => ({ role: item.role, content: item.content }));
      this.messages.push({ role: 'user', content: message });
      this.input = '';
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
        });
      } catch (error) {
        this.messages.push({ role: 'assistant', content: '네트워크 오류가 발생했습니다.' });
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
