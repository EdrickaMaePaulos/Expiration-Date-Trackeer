document.getElementById("get-started-button").addEventListener("click", function() {
    document.getElementById("get-started-container").style.display = "none";
    document.getElementById("signup-page-container").style.display = "block";
});

function revealWebsite() {
    document.getElementById("get-started-container").style.display = "none";
    document.getElementById("signup-page-container").style.display = "block";
}

function clearText(div) {
    if (div.innerText === div.getAttribute('data-placeholder')) {
        div.innerText = '';
    }
}

function restoreText(div) {
    if (div.innerText.trim() === '') {
        div.innerText = div.getAttribute('data-placeholder');
    }
}

document.querySelector(".input-container-1").addEventListener("click", function() {
    this.classList.add("active");
});

document.addEventListener("click", function(event) {
    let container = document.querySelector(".input-container-1");
    if (!container.contains(event.target)) {
        container.classList.remove("active");
    }
});

document.querySelector('.signin-button-1').addEventListener('click', function(event) {
    event.preventDefault();

    document.getElementById('signup-page-container').style.display = 'none';
    document.getElementById('signin-page-container').style.display = 'block';
});

document.querySelector('.signup-button-1').addEventListener('click', function(event) {
    event.preventDefault();

    document.getElementById('signup-page-container').style.display = 'none';
    document.getElementById('signin-page-container').style.display = 'block';
});

document.querySelector('.signup-button-2').addEventListener('click', function(event) {
    event.preventDefault();

    document.getElementById('signin-page-container').style.display = 'none';
    document.getElementById('signup-page-container').style.display = 'block';
});

document.querySelector('.signin-button-2').addEventListener('click', function(event) {
    event.preventDefault();

    document.getElementById('signin-page-container').style.display = 'none';
    document.getElementById('home-page-container').style.display = 'block';
});

document.addEventListener('DOMContentLoaded', () => {
    const icons = document.querySelectorAll('.nav-icon');
    const pages = {
        'home-icon': 'home-page-container',
        'list-icon': 'list-page-container',
        'settings-icon': 'settings-page-container',
        'about-icon': 'about-page-container'
    };

    icons.forEach(icon => {
        icon.addEventListener('click', (e) => {
            const iconId = e.currentTarget.id;
            const selectedPageId = pages[iconId];

            if (!selectedPageId) return;

            icons.forEach(i => i.classList.remove('active'));

            Object.values(pages).forEach(pageId => {
                const page = document.getElementById(pageId);
                if (page) page.style.display = 'none';
            });

            icon.classList.add('active');
            const selectedPage = document.getElementById(selectedPageId);
            if (selectedPage) selectedPage.style.display = 'block';
        });
    });
});

const storageItems = [
    '.refrigerator-1',
    '.freezer-1',
    '.pantry-1',
    '.medical-cabinet-1',
    '.personal-care-1'
];

storageItems.forEach(selector => {
    const item = document.querySelector(selector);
    if (item) {
        item.addEventListener('click', () => {
            const listIcon = document.getElementById('list-icon');
            if (listIcon) {
                listIcon.click();
            }
        });
    }
});

function toggleMenu(triggerElement) {
    document.querySelectorAll('.popup-menu').forEach(menu => {
        if (menu !== triggerElement.nextElementSibling) {
            menu.style.display = 'none';
        }
    });

    const menu = triggerElement.nextElementSibling;
    menu.style.display = menu.style.display === "block" ? "none" : "block;"
}

document.addEventListener('click', function(event) {
    const isInsidePopup = event.target.closest('.popup-menu');
    const isEllipsis = event.target.classList.contains('ellipsis');

    if (!isInsidePopup && !isEllipsis) {
        document.querySelector('.popup-menu').forEach(menu => {
            menu.style.display = 'none';
        });
    }
});

document.querySelector('.tagline-container').addEventListener('click', function(event) {
    event.preventDefault();

    document.getElementById('home-page-container').style.display = 'none';
    document.getElementById('about-page-container').style.display = 'block';
});

document.addEventListener('DOMContentLoaded', function() {
    const tabs = document.querySelectorAll('input[name="tab"]');

    const tabSections = document.querySelectorAll('.tab-section');

    tabs.forEach(tab => {
      tab.addEventListener('change', function() {
        tabSections.forEach(section => {
          section.style.display = 'none';
        });

        const activeTabId = this.id;
        const activeTabContent = document.querySelector(`.${activeTabId}-content`);

        activeTabContent.style.display = 'flex';
      });
    });

    document.querySelector('input[name="tab"]:checked').dispatchEvent(new Event('change'));
});

