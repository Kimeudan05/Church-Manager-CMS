document.addEventListener('DOMContentLoaded', function () {
    console.log("Connected");

    const navbarCollapse = document.querySelector('.navbar-collapse');

    if (!navbarCollapse) return;

    const navLinks = document.querySelectorAll(
        '.navbar-collapse .nav-link, .navbar-collapse .dropdown-item'
    );

    navLinks.forEach(link => {
        link.addEventListener('click', () => {
            if (navbarCollapse.classList.contains('show')) {
                const bsCollapse =
                    bootstrap.Collapse.getInstance(navbarCollapse) ||
                    new bootstrap.Collapse(navbarCollapse);

                bsCollapse.hide();
            }
        });
    });

    console.log(navbarCollapse);
});
