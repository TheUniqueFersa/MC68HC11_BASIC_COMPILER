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

      ORG $8000
INICIO
      LDS #$00FF
      JSR SERIAL


      CLR U1
      CLR U2
      CLR U3
      CLR U4
CICLATE
      LDAA #'?
      STAA ORDEN
CICLO
      LDAA ORDEN
      CMPA #'?
      BEQ  CICLO

      LDAB U1
      BNE  SIGUET
BORRA
      CLR U1
      CLR U2
      CLR U3
      CLR U4

      CMPA #'S
      BNE CICLATE
      STAA U1     * VALIDA S
      JMP CICLATE

SIGUET
      LDAB U2
      BNE  SIGUEA
      CMPA #'T
      BNE BORRA
      STAA U2     * VALIDA T
      JMP CICLATE

SIGUEA
      LDAB U3
      BNE  SIGUER
      CMPA #'A
      BNE BORRA
      STAA U3     * VALIDA A
      JMP CICLATE
      
SIGUER
      LDAB U4
      BNE  SIGUEF
      CMPA #'R
      BNE BORRA
      STAA U4     * VALIDA R
      JMP CICLATE

SIGUEF
      CMPA #'T
      BNE BORRA
EXITO
      LDAA #'E
      STAA ORDEN
      
      JMP EXITO

SERIAL

       LDD   #$302C  * CONFIGURA PUERTO SERIAL
       STAA  BAUD    * BAUD  9600  para cristal de 8MHz
       STAB  SCCR2   * HABILITA  RX Y TX PERO INTERRUPCN SOLO RX
       LDAA  #$00
       STAA  SCCR1   * 8 BITS

       LDAA  #$FE    * CONFIG PUERTO D COMO SALIDAS (EXCEPTO PD0)
       STAA  DDRD    * SEA  ENABLE DEL DISPLAY  PD4  Y RS PD3
                     
      
       LDAA  #$04
       STAA  HPRIO

       LDAA  #$00
       TAP
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
