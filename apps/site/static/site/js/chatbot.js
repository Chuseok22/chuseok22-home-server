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

      const history = this.messages.map((item) => ({ role: item.role, content: item.content }));
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
  // base.html의 hx-headers가 매 페이지 로드시 csrftoken 쿠키를 이미 설정해두므로 그대로 재사용한다.
  const match = document.cookie.match('(^|;)\\s*csrftoken\\s*=\\s*([^;]+)');
  return match ? decodeURIComponent(match[2]) : '';
}
