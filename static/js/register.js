// Handle form navigation and validation
function nextStep(currentStep) {
    // Validate current step
    if (!validateStep(currentStep)) return;
    
    // Hide current step
    document.querySelector(`[data-step="${currentStep}"]`).style.display = 'none';
    // Show next step
    document.querySelector(`[data-step="${currentStep + 1}"]`).style.display = 'block';
}

function prevStep(currentStep) {
    // Hide current step
    document.querySelector(`[data-step="${currentStep}"]`).style.display = 'none';
    // Show previous step
    document.querySelector(`[data-step="${currentStep - 1}"]`).style.display = 'block';
}

function validateStep(step) {
    let valid = true;
    const currentStep = document.querySelector(`[data-step="${step}"]`);
    
    // Validate required fields
    currentStep.querySelectorAll('input[required]').forEach(input => {
        if (!input.value) {
            valid = false;
            input.classList.add('error');
        } else {
            input.classList.remove('error');
        }
    });
    
    return valid;
}

// Handle role selection
document.querySelectorAll('.role-btn').forEach(btn => {
    btn.addEventListener('click', () => {
        // Remove selected class from all buttons
        document.querySelectorAll('.role-btn').forEach(b => b.classList.remove('selected'));
        // Add selected class to clicked button
        btn.classList.add('selected');
    });
});

// Add age option click effect
document.querySelectorAll('.age-option').forEach(option => {
    option.addEventListener('click', () => {
        document.querySelectorAll('.age-option').forEach(opt => {
            opt.classList.remove('selected');
        });
        option.classList.add('selected');
    });
});

// Add CSRF token function
function getCSRFToken() {
    const csrfInput = document.querySelector('[name=csrfmiddlewaretoken]');
    return csrfInput ? csrfInput.value : '';
}

// Handle form submission
document.getElementById('registrationForm').addEventListener('submit', async (e) => {
    e.preventDefault();
    
    // 获取选中的角色
    const selectedRole = document.querySelector('.role-btn.selected');
    const role = selectedRole ? selectedRole.dataset.role : 'family';  // 默认为family
    
    // 获取选中的年龄范围
    const selectedAge = document.querySelector('input[name="age"]:checked');
    
    // 检查必填字段
    const nickname = document.getElementById('nickname').value.trim();
    const familyName = document.getElementById('familyName').value.trim();
    
    if (!nickname || !familyName || !selectedAge) {
        alert('Please fill in all required fields');
        return;
    }
    
    const formData = {
        nickname: nickname,
        age_range: selectedAge.value,
        familyName: familyName,
        role: role,
        fertility: document.querySelector('input[name="fertility"]:checked')?.value || 'no_planning',
        preferences: Array.from(document.querySelectorAll('input[type="checkbox"]:checked'))
            .map(cb => cb.value)
    };

    try {
        const response = await fetch('/api/register/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify(formData)
        });

        const data = await response.json();
        
        if (response.ok) {
            alert('Registration successful!');
            window.location.href = '/login/';  // 注册成功后跳转到登录页
        } else {
            alert(data.message || 'Registration failed. Please try again.');
        }
    } catch (error) {
        console.error('Error:', error);
        alert('An error occurred. Please try again.');
    }
}); 