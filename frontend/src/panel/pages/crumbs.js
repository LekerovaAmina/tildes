// Хлебные крошки редакторов урока: Уровни и модули / B2 / Модуль 1 / Урок А / <раздел>
export function lessonCrumbs(lesson, lessonId, last) {
  if (!lesson) return [{ label: 'Уровни и модули', to: '/admin/levels' }, { label: last }]
  const level = `/admin/levels/${lesson.level_code}`
  return [
    { label: 'Уровни и модули', to: '/admin/levels' },
    { label: lesson.level_code, to: level },
    { label: `Модуль ${lesson.module_number}`, to: level },
    { label: `Урок ${lesson.letter}`, to: `/admin/lessons/${lessonId}` },
    { label: last },
  ]
}
