// Global site behavior: mobile sidebar toggle
document.addEventListener('DOMContentLoaded', () => {
  const toggleBtn = document.getElementById('sidebarToggle');
  const sidebar = document.querySelector('.sidebar');
  if (toggleBtn && sidebar) {
    toggleBtn.addEventListener('click', () => {
      sidebar.classList.toggle('show');
      sidebar.classList.toggle('collapsed');
    });
  }

  // Auto-dismiss alerts after 5 seconds
  document.querySelectorAll('.alert').forEach(alertEl => {
    setTimeout(() => {
      alertEl.classList.remove('show');
      alertEl.classList.add('fade');
    }, 5000);
  });
});
