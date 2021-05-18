class Log():
    def __init__(self, filename: str):
        self.fd = open(filename, "w")
    
    def log(self, data: str):
        self.fd.write(data + "\n")