document.addEventListener("DOMContentLoaded", function () {
    // Show selected CSV filename
    document.querySelectorAll('input[type="file"]').forEach(function (input) {
        input.addEventListener("change", function () {
            var label = input.closest(".csv-upload-area")?.querySelector(".csv-label");
            if (label && input.files.length > 0) {
                label.textContent = input.files[0].name;
            }
        });
    });
});
