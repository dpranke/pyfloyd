import js from "@eslint/js";

export default [
  js.configs.recommended, 
  {
    languageOptions: {
      globals: {
        'console': 'readonly',
        'process': 'readonly',
        'require': 'readonly',
      }
    }
  }
];
