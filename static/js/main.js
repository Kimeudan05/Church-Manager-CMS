console.log("Awesomely connected")

document.addEventListener('DOMContentLoaded', function () {
    const navbarToggler = document.getElementById('navbarToggler');
    const navbarCollapse = document.getElementById('navbarNav');

    // Toggle icon between hamburger and X
    navbarToggler.addEventListener('click', function () {
        const isCollapsed = navbarCollapse.classList.contains('show');
        if (!isCollapsed) {
            // Opening navbar → show X icon
            navbarToggler.innerHTML = '&times;'; // ×
        } else {
            // Closing navbar → show hamburger icon
            navbarToggler.innerHTML = '<span class="navbar-toggler-icon"></span>';
        }
    });

    // Close navbar when clicking outside
    document.addEventListener('click', function (event) {
        const isClickInside = navbarCollapse.contains(event.target) || navbarToggler.contains(event.target);
        if (!isClickInside && navbarCollapse.classList.contains('show')) {
            // Collapse the navbar
            const bsCollapse = bootstrap.Collapse.getInstance(navbarCollapse);
            bsCollapse.hide();
            // Reset icon
            navbarToggler.innerHTML = '<span class="navbar-toggler-icon"></span>';
        }
    });

    // Optional: reset icon when using ESC key
    navbarCollapse.addEventListener('hide.bs.collapse', function () {
        navbarToggler.innerHTML = '<span class="navbar-toggler-icon"></span>';
    });
});


console.log("Awesomely connected")