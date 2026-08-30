/** Strip everything but digits and cap at the 6-character code length. */
export const onlyDigits = (value: string): string => value.replace(/\D/g, '').slice(0, 6)
