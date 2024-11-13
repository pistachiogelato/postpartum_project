document.addEventListener('DOMContentLoaded', function() {
    const loginForm = document.getElementById('loginForm');

    loginForm.addEventListener('submit', async (e) => {
        e.preventDefault();
        
        const nickname = document.getElementById('nickname').value;
        const familyName = document.getElementById('familyName').value;
        
        //test
        console.log('Attempting login with:', {
            nickname,
            family_name: familyName
        });

        if (!nickname || !familyName) {
            alert('Please fill in all fields');
            return;
        }

        try {
            const response = await fetch('/api/login/', {
                method: 'POST',
                headers: {
                    'Content-Type': 'application/json',
                    'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                },
                body: JSON.stringify({
                    nickname: nickname,
                    family_name: familyName
                })
            });

            const data = await response.json();

            if (response.ok) {
                window.location.href = '/dashboard/';
            } else {
                alert(data.message || 'Login failed. Please try again.');
            }
        } catch (error) {
            console.error('Login error:', error);
            alert('An error occurred. Please try again.');
        }
    });
}); 