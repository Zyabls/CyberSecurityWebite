function addModule() {
    const container = document.getElementById('modules-container');
    const template = document.getElementById('module-template');
    const moduleElement = template.content.cloneNode(true);
    container.appendChild(moduleElement);
}

function removeModule(button) {
    const moduleItem = button.closest('.module-item');
    moduleItem.remove();
}

function addTest(button) {
    const moduleItem = button.closest('.module-item');
    const testContainer = moduleItem.querySelector('.test-container');
    const template = document.getElementById('test-template');
    const testElement = template.content.cloneNode(true);
    testContainer.appendChild(testElement);
}

function removeTest(button) {
    const testItem = button.closest('.test-item');
    testItem.remove();
}

function addQuestion(button) {
    const testItem = button.closest('.test-item');
    const questionContainer = testItem.querySelector('.questions-container');
    const template = document.getElementById('question-template');
    const questionElement = template.content.cloneNode(true);
    questionContainer.appendChild(questionElement);
}

function removeQuestion(button) {
    const questionItem = button.closest('.question-item');
    questionItem.remove();
}

// Add validation before form submission
document.querySelector('form').addEventListener('submit', function(event) {
    const modulesContainer = document.getElementById('modules-container');
    const modules = modulesContainer.querySelectorAll('.module-item');
    
    if (modules.length === 0) {
        event.preventDefault();
        alert('Please add at least one module to the course.');
        return;
    }

    // Validate each module has at least one test
    let valid = true;
    modules.forEach(module => {
        const tests = module.querySelectorAll('.test-item');
        if (tests.length === 0) {
            valid = false;
            event.preventDefault();
            alert('Each module must have at least one test.');
            return;
        }

        // Validate each test has at least one question
        tests.forEach(test => {
            const questions = test.querySelectorAll('.question-item');
            if (questions.length === 0) {
                valid = false;
                event.preventDefault();
                alert('Each test must have at least one question.');
                return;
            }
        });
    });
});
