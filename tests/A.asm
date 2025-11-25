; PROGRAMA DE PRUEBA CON ERRORES
; MCU: 68HC11
; Lógica general: recibir bytes por SCI y guardarlos en un buffer en RAM,
; llevando un contador. El código tiene errores sintácticos/semánticos
; a propósito para probar el compilador.

;-------------------------------------------------
; CONSTANTES Y REGISTROS
;-------------------------------------------------

SCSR      EQU   $102E      ; Registro de estado SCI
SCDR      EQU   $102F      ; Registro de datos SCI

LIMITE_OK EQU   $0A        ; 10 bytes a recibir
BUF_BASE  EQU   $0040      ; buffer en RAM

; NOTA: NO declaramos CONST_NO_DEF ni VAR_NO_DEF, etc.
; para provocar errores de constante/variable inexistente.

;-------------------------------------------------
; VARIABLES EN RAM
;-------------------------------------------------

        ORG   $0000

CONTADOR  RMB   1          ; contador de bytes recibidos
PTR_BUF   RMB   2          ; puntero al buffer

;-------------------------------------------------
; CÓDIGO PRINCIPAL EN ROM
;-------------------------------------------------

        ORG   $8000

INICIO:
        LDS   #$00FF       ; inicializa pila

        LDX   #BUF_BASE    ; X apunta al buffer
        STX   PTR_BUF

        LDAA  #LIMITE_OK   ; valor inicial correcto
        STAA  CONTADOR

;-------------------------------------------------
; 1) CONSTANTE INEXISTENTE
;-------------------------------------------------

        LDAA  #CONST_NO_DEF ; ERROR: constante inexistente
        CMPA  #LIMITE2      ; ERROR: constante inexistente (segunda vez)

;-------------------------------------------------
; 2) VARIABLE INEXISTENTE
;-------------------------------------------------

        STAA  VAR_NO_DEF    ; ERROR: variable inexistente
        LDAA  OTRA_VAR      ; ERROR: variable inexistente

;-------------------------------------------------
; BUCLE PRINCIPAL (parte "lógica")
;-------------------------------------------------

BUCLE_PRINCIPAL:
        LDAA  SCSR          ; lee estado SCI
        BITA  #$20          ; prueba bit RDRF
        BEQ   ESPERA_DATO   ; si no hay dato, esperar

        LDAA  SCDR          ; lee dato recibido

        LDX   PTR_BUF
        STAA  0,X
        INX
        STX   PTR_BUF

        DEC   CONTADOR
        BNE   BUCLE_PRINCIPAL

;-------------------------------------------------
; 3) ETIQUETA INEXISTENTE
;-------------------------------------------------

        BRA   FIN_OK        ; ERROR: etiqueta inexistente (FIN_OK no existe)

ESPERA_DATO:
        NOP
        BRA   BUCLE_PRINCIPAL

;-------------------------------------------------
; 4) MNEMÓNICO INEXISTENTE
;-------------------------------------------------

        COMPA #$10          ; ERROR: mnemónico inexistente (no está en el set)
        LOADD #$1234        ; ERROR: otro mnemónico inexistente

;-------------------------------------------------
; 5) INSTRUCCIÓN CARECE DE OPERANDOS
;-------------------------------------------------

        LDAA  #$01          ; correcta
        STAA                ; ERROR: STAA requiere operando

        LDAB  #$02          ; correcta
        CMPA                ; ERROR: CMPA requiere operando

;-------------------------------------------------
; 6) INSTRUCCIÓN NO LLEVA OPERANDOS
;-------------------------------------------------

        INX                 ; correcta (implícita)
        MUL   2,X           ; ERROR: MUL no lleva operandos

        DEX   CONTADOR      ; ERROR: DEX no lleva operandos

;-------------------------------------------------
; 7) MAGNITUD DE OPERANDO ERRÓNEA
;-------------------------------------------------

        LDAA  #$1789        ; ERROR: inmediato excede 8 bits
        LDAB  #300          ; ERROR: 300 > 255, no cabe en 8 bits

        LDX   #$123456      ; ERROR: excede 16 bits de X

;-------------------------------------------------
; 8) SALTO RELATIVO MUY LEJANO
;-------------------------------------------------

        BEQ   MUY_LEJOS     ; ERROR: salto relativo fuera de rango
                            ; MUY_LEJOS está muy lejos (otro ORG)

;-------------------------------------------------
; 9) INSTRUCCIÓN SIN ESPACIO DESDE EL MARGEN
;    (solo las etiquetas van pegadas al margen)
;-------------------------------------------------

LDAA  #$55                 ; ERROR: instrucción pegada al margen sin ser etiqueta
STAA  CONTADOR             ; ERROR: repetido mismo tipo

;-------------------------------------------------
; MOVEMOS EL CONTADOR DE UBICACIÓN PARA EL SALTO LEJANO
;-------------------------------------------------

        ORG   $8300

MUY_LEJOS:
        NOP
        RTS

;-------------------------------------------------
; 10) VECTOR DE RESET (SIN ERROR)
;    (aquí no hay error, es solo para coherencia del programa)
;-------------------------------------------------

        ORG   $FFFE

VEC_RESET:
        FCB   $80,$00       ; vector de reset a $8000

;-------------------------------------------------
; 10) NO SE ENCUENTRA END
;-------------------------------------------------
; ERROR: falta la directiva END al final del archivo
; (tu compilador debe reportar “NO SE ENCUENTRA END”)
