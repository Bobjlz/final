# works for python 3.5+
import string, secrets
N = int(input("length of random string?"))
print(''.join(secrets.choice(string.ascii_uppercase + string.digits) for _ in range(N)))