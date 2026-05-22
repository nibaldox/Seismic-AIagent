/* Help center JS — tabs, FAQ expanders, feedback form */

window.addEventListener('DOMContentLoaded', () => {
  // FAQ expanders already handled by CSS <details> element
});

function submitFeedback() {
  const type = document.getElementById('feedback-type')?.value;
  const text = document.getElementById('feedback-text')?.value;
  const email = document.getElementById('feedback-email')?.value;
  if (!text) { showToast('Escribe tu mensaje', 'warning'); return; }
  // In a real implementation this would POST to an endpoint
  showToast('Gracias por tu comentario', 'success');
  if (document.getElementById('feedback-form')) {
    document.getElementById('feedback-form').reset();
  }
}

window.submitFeedback = submitFeedback;
window.showToast = showToast;