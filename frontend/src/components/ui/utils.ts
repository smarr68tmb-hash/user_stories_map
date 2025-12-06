type ClassValue = string | number | null | undefined | boolean | ClassValue[];

export function cn(...classes: ClassValue[]): string {
  return classes.flat(Infinity).filter(Boolean).join(' ');
}

