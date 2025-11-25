  ORG     $8000

  hol LDAA    $45AS     A   # ; carga 8 bits (alto de 457C si era necesario)
  LDAB    $7C        ; carga 8 bits (bajo de 457C)

  LDAB    $31        ; valor válido para 8 bits (corrección)

  LDD     $1789      ; carga 16 bits al registro D

  LDX     $FDE8      ; 65000 decimal → FDE8h

  ADDA    $7C        ; A = A + 7Ch

  ANDA    $F0        ; solo 8 bits válidos para ANDA

  LDY     $ABCD      ; carga 16 bits al registro Y

  END
