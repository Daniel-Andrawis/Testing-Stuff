document.addEventListener('DOMContentLoaded', function() {
    document.querySelectorAll('.flash').forEach(function(el) {
        setTimeout(function() { el.remove(); }, 5000);
    });
});
