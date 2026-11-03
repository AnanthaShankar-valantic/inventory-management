// Returns 'YYYY-MM' read from the date string itself, or null when it is not a date string.
// Why not new Date(): 'YYYY-MM-DD' parses as UTC midnight, so local getMonth() gives the previous
// month west of UTC, and toISOString() throws a RangeError on invalid input.
export const monthOf = (d) => (typeof d === 'string' && /^\d{4}-(0[1-9]|1[0-2])/.test(d) ? d.slice(0, 7) : null)
