import socket

def is_connected():
    """
    Verifica la connettività a Internet provando a stabilire una connessione
    a un server esterno affidabile (DNS di Google sulla porta DNS).
    Restituisce True se la connessione ha successo, altrimenti False.
    """
    try:
        # Usiamo create_connection che tenta sia di risolvere l'hostname 
        # (se dato) che di connettersi. Usare un IP diretto come "8.8.8.8"
        # è una prova eccellente di connettività di rete esterna.
        # La porta 53 è quella standard per il DNS.
        socket.create_connection(("8.8.8.8", 53), timeout=3)
        return True
    except OSError:
        # Questo cattura errori come timeout, "Network is unreachable", etc.
        return False