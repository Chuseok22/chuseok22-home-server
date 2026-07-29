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
  // 페이지 응답 어딘가에서 {{ csrf_token }}이 렌더링되면(현재는 base.html의 hx-headers
  // 속성이 그 용도) Django의 get_token() 호출로 csrftoken 쿠키가 설정된다. 이 함수는 그
  // 쿠키를 읽어 재사용할 뿐이며, hx-headers 자체에 종속된 동작이 아니다.
  const match = document.cookie.match('(^|;)\\s*csrftoken\\s*=\\s*([^;]+)');
  return match ? decodeURIComponent(match[2]) : '';
}
