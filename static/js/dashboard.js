// ===============================
// Utility Functions
// ===============================
function getCSRFToken() {
    const name = 'csrftoken';
    let cookieValue = null;
    
    if (document.cookie && document.cookie !== '') {
        const cookies = document.cookie.split(';');
        for (let i = 0; i < cookies.length; i++) {
            const cookie = cookies[i].trim();
            if (cookie.substring(0, name.length + 1) === (name + '=')) {
                cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                break;
            }
        }
    }
    return cookieValue;
}

// ===============================
// Mood Tracking Module
// ===============================
// Mood Tracking Module
function initializeMoodTracking() {
    // Get elements from DOM
    const moodSlider = document.querySelector('.mood-slider');
    const moodValue = document.querySelector('.mood-value');
    const encouragement = document.querySelector('.encouragement');
    
    // Check if elements exist
    if (!moodSlider || !moodValue || !encouragement) {
        console.warn('[Debug] Required mood tracking elements not found');
        return;
    }

    console.log('[Debug] Initializing mood tracking');

    // Function to update mood display
    function updateMoodDisplay(value) {
        // Update mood value display
        moodValue.textContent = value;
        
        // Update encouragement message only for admin
        if (!moodSlider.disabled) {
            const messages = {
                low: "Things will get better. We're here for you!",
                medium: "You're doing great! Keep going!",
                high: "Wonderful! Your positive energy is contagious!"
            };
            
            encouragement.textContent = value < 30 ? messages.low : 
                                      value < 60 ? messages.medium : 
                                      messages.high;
        }
                                  
        console.log('[Debug] Updated mood display:', { value, message: encouragement.textContent });
    }

    // Function to handle mood changes (only for admin)
    function handleMoodChange(e) {
        if (moodSlider.disabled) return; // Skip if not admin
        
        const value = e.target.value;
        console.log('[Debug] Mood slider changed:', value);
        updateMoodDisplay(value);
        saveMoodValue(value);
    }

    // Set initial display
    updateMoodDisplay(moodSlider.value);

    // Add event listeners only if user is admin
    if (!moodSlider.disabled) {
        moodSlider.addEventListener('input', (e) => updateMoodDisplay(e.target.value));
        moodSlider.addEventListener('change', handleMoodChange);
    }
}

// Helper function to save mood value
async function saveMoodValue(value) {
    try {
        console.log('[Debug] Saving mood value:', value);
        const response = await fetch('/update-mood/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            },
            body: JSON.stringify({ mood: value })
        });

        const data = await response.json();
        console.log('[Debug] Mood update response:', data);
        
        if (data.status !== 'success') {
            throw new Error(data.message || 'Failed to update mood');
        }
    } catch (error) {
        console.error('[Debug] Error updating mood:', error);
        alert('Failed to update mood. Please try again.');
    }
}


// ===============================
// Art Display Module
// ===============================

// Handle keyword form submission
function handleKeywordSubmit(event) {
    event.preventDefault();
    const keywordInput = document.getElementById('keyword');
    const keyword = keywordInput.value.trim();
    
    if (!keyword) return;

    fetch('/api/submit-family-keyword/', {
        method: 'POST',
        headers: {
            'Content-Type': 'application/json',
            'X-CSRFToken': getCSRFToken()
        },
        body: JSON.stringify({ keyword: keyword })
    })
    .then(response => response.json())
    .then(data => {
        if (data.status === 'success') {
            keywordInput.value = '';  // Clear input after successful submission
            updateArtDisplay();  // Refresh the display
        }
    })
    .catch(error => console.error('Error submitting keyword:', error));
}

// Add event listener for keyword form
document.getElementById('keywordForm').addEventListener('submit', handleKeywordSubmit);

// Update art display with current data
async function updateArtDisplay() {
    console.log('[Debug] Starting art display update');
    const artDisplay = document.getElementById('artDisplay');
    const keywordsList = document.getElementById('keywordsList');
    const remainingSlots = document.getElementById('remainingSlots');

    try {
        // Fetch current art data
        const response = await fetch('/api/family-art-daily/');
        const data = await response.json();
        console.log('[Debug] Art data received:', data);

        if (data.status === 'success') {
            // Update keywords display
            if (keywordsList) {
                const keywordsHtml = data.data.keywords.map(keyword =>
                    `<div class="keyword-tag">${keyword}</div>`
                ).join('');
                keywordsList.innerHTML = keywordsHtml;
            }

            // Update remaining slots
            if (remainingSlots) {
                remainingSlots.textContent = `${data.data.remaining_slots} keywords remaining`;
            }

            // Update art display
            if (artDisplay) {
                if (data.data.image_url) {
                    console.log('[Debug] Attempting to display image:', data.data.image_url);
                    artDisplay.innerHTML = `
                        <div class="art-image-container">
                            <img 
                                src="${data.data.image_url}" 
                                alt="Family Art" 
                                class="family-art-image"
                                onerror="this.onerror=null; handleImageError(this);"
                                onload="console.log('Image loaded successfully')"
                            >
                            <div class="art-description">
                                <p>Created with: ${data.data.keywords.join(', ')}</p>
                            </div>
                        </div>
                    `;
                } else if (data.data.keywords.length === 3) {
                    // Show generation status
                    if (data.data.generation_status === 'failed') {
                        artDisplay.innerHTML = `
                            <div class="art-error">
                                <p>Image generation failed</p>
                                <p class="error-message">${data.data.error_message || 'Please try again'}</p>
                                <button onclick="window.retryGeneration()" class="retry-btn">Retry Generation</button>
                            </div>
                        `;
                    } else {
                        artDisplay.innerHTML = `
                            <div class="art-loading">
                                <p>Generating your family art...</p>
                                <div class="loading-spinner"></div>
                            </div>
                        `;
                    }
                }
            }

            // Update submit button state
            const submitButton = document.getElementById('submitKeyword');
            if (submitButton) {
                submitButton.disabled = data.data.remaining_slots === 0;
            }
        } else {
            console.error('[Debug] Error in art data:', data.message);
            artDisplay.innerHTML = `
                <div class="art-error">
                    <p>Error loading art data</p>
                    <p class="error-message">${data.message}</p>
                </div>
            `;
        }
    } catch (error) {
        console.error('[Debug] Error updating art display:', error);
        artDisplay.innerHTML = `
            <div class="art-error">
                <p>Error updating display</p>
                <p class="error-message">${error.message}</p>
            </div>
        `;
    }
}

// Handle image loading errors
function handleImageError(img) {
    console.error('[Debug] Image failed to load:', img.src);
    const container = img.closest('.art-image-container');
    if (container) {
        container.innerHTML = `
            <div class="art-error">
                <p>Failed to load image</p>
                <button onclick="window.retryGeneration()" class="retry-btn">Retry Generation</button>
            </div>
        `;
    }
}

// Retry image generation
async function retryGeneration() {
    console.log('[Debug] Retrying image generation');
    try {
        const response = await fetch('/api/retry-generation/', {
            method: 'POST',
            headers: {
                'Content-Type': 'application/json',
                'X-CSRFToken': getCSRFToken()
            }
        });
        
        const data = await response.json();
        if (data.status === 'success') {
            updateArtDisplay();  // Refresh display with new image
        } else {
            throw new Error(data.message || 'Retry failed');
        }
    } catch (error) {
        console.error('[Debug] Retry generation error:', error);
        alert('Failed to retry image generation. Please try again later.');
    }
}

// Make retryGeneration available globally
window.retryGeneration = retryGeneration;



// ===============================
// Task Management Module
// ===============================
function initializeTaskEvents() {
    const taskItems = document.querySelectorAll('.task-item input[type="checkbox"]');
    
    taskItems.forEach(checkbox => {
        checkbox.addEventListener('change', async function() {
            const taskId = this.closest('.task-item').dataset.taskId;
            try {
                const response = await fetch('/api/tasks/update-status/', {
                    method: 'POST',
                    headers: {
                        'Content-Type': 'application/json',
                        'X-CSRFToken': getCSRFToken()
                    },
                    body: JSON.stringify({
                        task_id: taskId,
                        completed: this.checked
                    })
                });
                
                const data = await response.json();
                if (data.status !== 'success') {
                    console.error('Failed to update task:', data.message);
                    this.checked = !this.checked; // 恢复原状态
                }
            } catch (error) {
                console.error('Error updating task:', error);
                this.checked = !this.checked; // 恢复原状态
            }
        });
    });
}

// Function to load tasks from server
async function loadTodayTasks() {
    console.log('[Debug] Loading today\'s tasks');
    const tasksList = document.querySelector('.tasks-list');
    
    try {
        // Show loading state
        tasksList.innerHTML = `
            <div class="loading-tasks">
                <p>Loading your daily tasks...</p>
            </div>
        `;
        
        const response = await fetch('/api/tasks/today/');
        const data = await response.json();
        
        if (data.status === 'success') {
            updateTaskDisplay(data.tasks);
        } else {
            throw new Error(data.message);
        }
        
    } catch (error) {
        console.error('[Debug] Error loading tasks:', error);
        tasksList.innerHTML = `
            <div class="error-message">
                <p>Error loading tasks. Please try again.</p>
                <button onclick="loadTodayTasks()">Retry</button>
            </div>
        `;
    }
}

// Function to update task display
function updateTaskDisplay(tasks) {
    console.log('[Debug] Updating task display');
    const tasksList = document.querySelector('.tasks-list');
    if (!tasksList) {
        console.warn('[Debug] Tasks list container not found');
        return;
    }
    
    if (!tasks || tasks.length === 0) {
        tasksList.innerHTML = `
            <div class="no-tasks">
                <p>No tasks available</p>
            </div>
        `;
        return;
    }
    
    tasksList.innerHTML = tasks.map(task => `
        <div class="task-item" data-task-id="${task.id}" data-task-type="${task.task_type}">
            <input type="checkbox" 
                   id="task-${task.id}" 
                   ${task.completed ? 'checked' : ''}>
            <div class="task-content">
                <label for="task-${task.id}">${task.description}</label>
            </div>
        </div>
    `).join('');
    
    // Reinitialize event listeners for new tasks
    initializeTaskEvents();
}

// ===============================
// Quiz Module
// ===============================
function showQuizResult(result, container) {
    console.log('[Debug] Showing quiz result:', result);  // Add debug logging
    container.innerHTML = `
        <div class="quiz-result fade-in">
            <h3>${result.is_correct ? '🎉 Correct!' : '😊 Nice Try!'}</h3>
            <p>${result.is_correct ? 
                `Great job! You earned ${result.points_earned} points!` : 
                `The correct answer was: ${result.correct_answer}`
            }</p>
            <div class="quiz-explanation mt-3">
                <p><strong>Explanation:</strong> ${result.explanation || 'No explanation available'}</p>
            </div>
        </div>
    `;
}
function displayQuiz(quiz) {
    const quizContainer = document.querySelector('.quiz-container');
    if (!quizContainer) return;
    
    quizContainer.innerHTML = `
        <div class="quiz-card">
            <div class="quiz-question">${quiz.question}</div>
            <div class="quiz-options">
                ${quiz.options.map((option, index) => `
                    <button class="quiz-option" data-index="${index}">${option}</button>
                `).join('')}
            </div>
        </div>
    `;
}

function initializeQuizSystem() {
    const feifeiContainer = document.querySelector('.feifei-container');
    const quizContainer = document.querySelector('.quiz-container');
    
    if (!feifeiContainer || !quizContainer) return;
    
    feifeiContainer.addEventListener('click', async () => {
        try {
            quizContainer.innerHTML = `
                <div class="quiz-loading">
                    <p>Loading your daily health quiz...</p>
                </div>
            `;

            const response = await fetch('/api/daily-quiz/');
            const data = await response.json();
            console.log('[Debug] Quiz data received:', data);  // Add debug logging
            
            if (data.status === 'success') {
                const quiz = data.quiz;
                if (quiz.answered) {
                    // If already answered, show previous result
                    const previousAnswer = await fetch(`/api/quiz-result/${quiz.id}/`);
                    const resultData = await previousAnswer.json();
                    if (resultData.status === 'success') {
                        showQuizResult(resultData, quizContainer);
                    } else {
                        quizContainer.innerHTML = `
                            <div class="quiz-message">
                                <p>You've already completed today's quiz! Come back tomorrow for a new one! 😊</p>
                            </div>
                        `;
                    }
                    return;
                }
                
                // Show new quiz if not answered
                quizContainer.innerHTML = `
                    <div class="quiz-card fade-in">
                        <h3>Today's Health Quiz</h3>
                        <p class="quiz-question">${quiz.question}</p>
                        <div class="quiz-options">
                            ${quiz.options.map((option, index) => `
                                <button class="quiz-option" data-answer="${index}">
                                    ${option}
                                </button>
                            `).join('')}
                        </div>
                    </div>
                `;
                
                // Add click handlers for options
                document.querySelectorAll('.quiz-option').forEach(button => {
                    button.addEventListener('click', async () => {
                        // Add debug logging to see what's being clicked
                        const clickedOption = button.textContent.trim();
                        const answer = parseInt(button.dataset.answer, 10);
                        
                        console.log('[Debug] Quiz option clicked:', {
                            optionText: clickedOption,
                            optionIndex: answer,
                            allOptions: quiz.options
                        });
                        
                        try {
                            const response = await fetch('/api/answer-quiz/', {
                                method: 'POST',
                                headers: {
                                    'Content-Type': 'application/json',
                                    'X-CSRFToken': getCSRFToken()
                                },
                                body: JSON.stringify({
                                    quiz_id: quiz.id,
                                    answer: answer
                                })
                            });
                            
                            const result = await response.json();
                            // Add more detailed debug logging
                            console.log('[Debug] Answer submission result:', {
                                result,
                                submittedAnswer: answer,
                                isCorrect: result.is_correct
                            });
                            
                            if (result.status === 'success') {
                                showQuizResult(result, quizContainer);
                            } else {
                                throw new Error(result.message);
                            }
                        } catch (error) {
                            console.error('[Debug] Error submitting answer:', error);
                            quizContainer.innerHTML = `
                                <div class="quiz-error">
                                    <p>Error submitting answer. Please try again!</p>
                                    <p class="error-details">${error.message}</p>
                                </div>
                            `;
                        }
                    });
                });
            }
        } catch (error) {
            console.error('[Debug] Error loading quiz:', error);
            quizContainer.innerHTML = `
                <div class="quiz-error">
                    <p>Sorry, couldn't load the quiz right now. Please try again later!</p>
                    <p class="error-details">${error.message}</p>
                </div>
            `;
        }
    });
}


// ===============================
// Main Initialization
// ===============================
document.addEventListener('DOMContentLoaded', function() {
    console.log('[Debug] Initializing dashboard components...');
    
    // Initialize all modules
    updateArtDisplay();
    initializeMoodTracking();
    initializeQuizSystem();
    loadTodayTasks(); // Load tasks first
    initializeTaskEvents();
});


