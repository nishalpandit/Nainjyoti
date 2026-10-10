// Lightweight progressive enhancement only; admin actions and persistence belong to the backend.
document.addEventListener('click', function (event) {
  const trigger = event.target.closest('[data-dismiss-notice]');
  if (trigger) trigger.closest('.notice')?.remove();
});
