* PROGRAMA START

*DECLARACION CONSTANTES

SCDR   EQU   $102F
SCCR2  EQU   $102D
SCSR   EQU   $102E
SCCR1  EQU   $102C
BAUD   EQU   $102B
HPRIO  EQU   $103C
SPCR   EQU   $1028
CSCTL  EQU   $105D
OPT2   EQU   $1038
DDRD   EQU   $1009

*DECLARACION DE VARIABLES

ORDEN EQU $0000
U1    EQU $0001
U2    EQU $0002
U3    EQU $0003
U4    EQU $0004
U5    EQU $0005
A1    EQU $0006
A2    EQU $0007
A3    EQU $0008
A4    EQU $0009
A5    EQU $000A
VAR16 EQU $0010

      ORG $8000
INICIO
      LDS #$00FF
      


      CLR A1
      CLR A2
      CLR A3
      CLR A4
      CLR A5
      
      CLR U1
      CLR U2
      CLR U3
      CLR U4
      CLR U5

EXITO
      LDX #$FFFF
LOOP
      STX  VAR16
      XGDX
      JSR BINBCD
      LDX  VAR16
      DEX
      BEQ  INICIO
      JSR  ESPERA
      JMP  LOOP

ESPERA
       LDY #$00FF
DECREMENTA       
       DEY
       BNE  DECREMENTA
       RTS     




***********************************
* CONVIERTE A BCD
***********************************

BINBCD
     
      LDX  #$2710
      IDIV 
      XGDX
      STAB U1
      ADDB #$30
      STAB A1
      XGDX
      LDX  #$3E8
      IDIV
      XGDX
      STAB U2
      ADDB #$30
      STAB A2
      XGDX
      LDX  #$64
      IDIV
      XGDX
      STAB U3
      ADDB #$30
      STAB A3
      XGDX
      LDX  #$A
      IDIV
      XGDX
      STAB U4
      ADDB #$30
      STAB A4
      XGDX
      STAB U5
      ADDB #$30
      STAB A5


      RTS
      
***********************************
* ATENCION A INTERRUPCION SERIAL
***********************************
       ORG  $F100

       LDAA SCSR
       LDAA SCDR
       STAA ORDEN
         
       RTI

***********************************
* VECTOR INTERRUPCION SERIAL
***********************************
       ORG   $FFD6
       FCB   $F1,$00       


***********************************
*RESET
***********************************
       ORG    $FFFE
RESET  FCB    $80,$00
***********************************
       END   $8000
