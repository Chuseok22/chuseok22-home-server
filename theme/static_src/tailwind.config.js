/**
 * This is a minimal config.
 *
 * If you need the full config, get it from here:
 * https://unpkg.com/browse/tailwindcss@latest/stubs/defaultConfig.stub.js
 */

module.exports = {
    // apps/site/templatetags/activity_tags.py의 contribution_level_class가
    // 템플릿에 리터럴로 나타나지 않는 클래스명을 동적으로 반환하므로 safelist로 강제 포함한다.
    safelist: [
        'bg-base-300',
        'bg-success/30',
        'bg-success/55',
        'bg-success/80',
        'bg-success',
    ],
    content: [
        /**
         * HTML. Paths to Django template files that will contain Tailwind CSS classes.
         */

        /*  Templates within theme app (<tailwind_app_name>/templates), e.g. base.html. */
        '../templates/**/*.html',

        /*
         * Main templates directory of the project (BASE_DIR/templates).
         * Adjust the following line to match your project structure.
         */
        '../../templates/**/*.html',

        /*
         * Templates in other django apps (BASE_DIR/<any_app_name>/templates).
         * Adjust the following line to match your project structure.
         */
        '../../**/templates/**/*.html',

        /**
         * JS: If you use Tailwind CSS in JavaScript, uncomment the following lines and make sure
         * patterns match your project structure.
         */
        /* JS 1: Ignore any JavaScript in node_modules folder. */
        // '!../../**/node_modules',
        /* JS 2: Process all JavaScript files in the project. */
        // '../../**/*.js',

        /**
         * Python: If you use Tailwind CSS classes in Python, uncomment the following line
         * and make sure the pattern below matches your project structure.
         */
        // '../../**/*.py'
    ],
    theme: {
        extend: {},
    },
    plugins: [
        /**
         * '@tailwindcss/forms'의 기본 strategy('base')는 bare <select>/<input>/<textarea>
         * 태그 셀렉터에 전역 리셋을 주입해 DaisyUI의 .select/.input 클래스 스타일과 충돌한다
         * (강좌 조회 드롭다운이 매우 좁게 렌더링되는 버그의 원인이었다 - GitHub 이슈 #164).
         * 프로젝트 전체가 DaisyUI의 select-bordered/input-bordered 클래스만 쓰고
         * form-select/form-input 접두 클래스는 쓰지 않으므로, strategy: 'class'로 바꿔
         * bare 태그 리셋 자체를 끈다.
         */
        require('@tailwindcss/forms')({ strategy: 'class' }),
        require('@tailwindcss/typography'),
        require('@tailwindcss/aspect-ratio'),
        require('daisyui'),
    ],
}
