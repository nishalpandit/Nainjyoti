// Small progressive enhancement: dismissible informational notices only.
document.addEventListener('click', function (event) {
  const button = event.target.closest('[data-dismiss-notice]');
  if (button) button.closest('.alert')?.remove();
});