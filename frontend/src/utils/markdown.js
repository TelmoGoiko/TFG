const slugify = (value) => {
  return value
    .toLowerCase()
    .replace(/[^a-z0-9\s-]/g, '')
    .trim()
    .replace(/\s+/g, '-')
}

const createBlockFileName = (order, title) => {
  const leftPadded = String(order + 1).padStart(2, '0')
  return `${leftPadded}_${slugify(title)}.md`
}

export { slugify, createBlockFileName }
