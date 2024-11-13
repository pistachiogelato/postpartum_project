document.addEventListener('DOMContentLoaded', function() {
    const settingsForm = document.getElementById('settingsForm');

    if (settingsForm) {
        settingsForm.addEventListener('submit', async function(e) {
            e.preventDefault();

            const formData = {
                nickname: document.getElementById('nickname').value,
                fertility_status: document.getElementById('fertilityStatus').value,
                emotional_support: document.querySelector('input[name="emotional_support"]').checked,
                health_wellness: document.querySelector('input[name="health_wellness"]').checked,
                family_activities: document.querySelector('input[name="family_activities"]').checked
            };

            try {
                const response = await fetch('/api/update-settings/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': document.querySelector('[name=csrfmiddlewaretoken]').value
                    },
                    body: JSON.stringify(formData)
                });

                const data = await response.json();

                if (response.ok) {
                    alert('Settings updated successfully');
                    window.location.href = '/dashboard/';
                } else {
                    alert(data.message || 'Failed to update settings');
                }
            } catch (error) {
                console.error('Error:', error);
                alert('An error occurred. Please try again.');
            }
        });
    }
}); 