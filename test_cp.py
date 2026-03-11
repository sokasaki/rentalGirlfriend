from app import app, inject_user_type

def test_cp():
    with app.test_request_context():
        ctx = inject_user_type()
        print("KEYS IN CONTEXT:", ctx.keys())
        if 'has_perm' in ctx:
            print("has_perm is present!")
        else:
            print("ERROR: has_perm MISSING!")

if __name__ == '__main__':
    test_cp()
