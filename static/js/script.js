// Flash message auto-close
document.addEventListener('DOMContentLoaded', function() {
    // Auto-close flash messages after 5 seconds
    const alerts = document.querySelectorAll('.alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.animation = 'slideOut 0.3s ease';
            setTimeout(() => alert.remove(), 300);
        }, 5000);
    });
});

// Add slide out animation
const style = document.createElement('style');
style.textContent = `
    @keyframes slideOut {
        to {
            transform: translateY(-10px);
            opacity: 0;
        }
    }
`;
document.head.appendChild(style);

// File input display filename
document.querySelectorAll('input[type="file"]').forEach(input => {
    input.addEventListener('change', function(e) {
        const fileName = e.target.files[0]?.name;
        const label = this.nextElementSibling;
        if (fileName && label) {
            const textSpan = label.querySelector('.file-text');
            if (textSpan) {
                textSpan.textContent = fileName;
            }
        }
    });
});