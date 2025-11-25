; PROGRAMA 1: CONSTANTE INEXISTENTE

        ORG   $8000

        LDAA  #CONST_NO_DEF      ; ERROR: constante inexistente

        SWI
        END  $8000
